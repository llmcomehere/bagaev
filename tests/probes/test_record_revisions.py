"""Literal revision lineage, refusal and exact source handoff controls."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
import bagaev_record_revisions as r
import record_revisions as cli


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def source(number):
    return ('bagaev record-form/5; program { entry main; fn main() -> Int64 = '
            + str(number) + '; }').encode()


def program_pin(number):
    # Literal expected decoded shape, independent of implementation/decoder.
    return sha(canonical({'schema': 'bagaev-typed-record/11', 'records': {},
        'lists': {}, 'variants': {}, 'entry': 'main',
        'functions': {'main': {'params': [], 'result': 'Int64', 'body': ['int', number]}}}))


class RevisionsTests(unittest.TestCase):
    def test_inventory_handoff(self):
        original = (ROOT/'examples/probes/inventory-reserve/Reserve.bagaev').read_bytes()
        candidate = (ROOT/'examples/probes/inventory-change/ReserveLimited.bagaev').read_bytes()
        raw_a = 'bc2a580e7c5fcfa9bd7287255850af73b7ffa7a23fafb53f10b7fbea9d6e63aa'
        raw_b = '8df61c88b2150258a560e019ed4920e3aa8fb393708a9c1f720aa9ae961d7005'
        self.assertEqual(sha(original), raw_a)
        self.assertEqual(sha(candidate), raw_b)
        first = r.initialize(original, source_sha256=raw_a,
            program_sha256='753f14412252805ee3eeae9c2a659d076922c28fd12f316cee57654677db8c6a')
        second = r.append(first, candidate, source_sha256=raw_b,
            program_sha256='c403f4e482ee607dab12737dc66befef015f4499ffafd58ef75329362a20a915',
            expected_package_sha256=sha(canonical(first)), expected_head=first['head'])
        fresh = r.loads(canonical(second))
        self.assertEqual(r.checkout(fresh, first['head']), original)
        self.assertEqual(r.checkout(fresh, second['head']), candidate)
        self.assertNotIn(b'order-limit', original)
        self.assertIn(b'order-limit', candidate)

    def first(self):
        return r.initialize(source(0), source_sha256=sha(source(0)), program_sha256=program_pin(0))

    def add(self, package, number):
        return r.append(package, source(number), expected_package_sha256=sha(canonical(package)),
            expected_head=package['head'], source_sha256=sha(source(number)), program_sha256=program_pin(number))

    def refusal(self, code, fn, *args, **kwargs):
        with self.assertRaises(r.RevisionError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_literal_identity_history_and_revert(self):
        first = self.first()
        expected = sha(canonical({'parent': None, 'source_sha256': sha(source(0)),
                                  'program_sha256': program_pin(0)}))
        self.assertEqual(first['head'], expected)
        old = copy.deepcopy(first)
        second = self.add(first, 1)
        self.assertEqual(first, old)
        self.assertEqual(second['revisions'][0], first['revisions'][0])
        restored = r.loads(canonical(second))
        self.assertEqual(r.checkout(restored, expected), source(0))
        self.assertEqual(r.checkout(restored, restored['head']), source(1))
        reverted = self.add(second, 0)
        self.assertNotEqual(reverted['head'], expected)
        self.assertFalse(r.inspect(reverted)['semantic_check'])
        self.assertFalse(r.inspect(reverted)['execution_admission'])

    def test_stale_and_noop(self):
        first = self.first()
        second = self.add(first, 1)
        kw = dict(expected_package_sha256=sha(canonical(second)), expected_head=first['head'],
                  source_sha256=sha(source(2)), program_sha256=program_pin(2))
        self.refusal('REVISION_STALE_HEAD', r.append, second, source(2), **kw)
        kw.update(expected_head=second['head'], expected_package_sha256=sha(canonical(first)))
        self.refusal('REVISION_STALE_PACKAGE', r.append, second, source(2), **kw)
        self.refusal('REVISION_NO_CHANGE', self.add, first, 0)

    def test_tampered_full_history(self):
        second = self.add(self.first(), 1)
        for field, value, code in [('source', source(2).decode(), 'REVISION_SOURCE_PIN'),
                                    ('parent', '0'*64, 'REVISION_LINEAGE'),
                                    ('id', '0'*64, 'REVISION_ID')]:
            bad = copy.deepcopy(second)
            bad['revisions'][1][field] = value
            self.refusal(code, r.checkout, bad, bad['revisions'][0]['id'])
        for key, value, code in [('form', 'record-form/6', 'REVISION_PROFILE'),
                                ('semantic_check', True, 'REVISION_ASSURANCE'),
                                ('head', '0'*64, 'REVISION_HEAD')]:
            bad = copy.deepcopy(second); bad[key] = value
            self.refusal(code, r.validate, bad)
        bad = copy.deepcopy(second); bad['extra'] = False
        self.refusal('REVISION_SHAPE', r.validate, bad)
        self.refusal('REVISION_NOT_FOUND', r.checkout, second, '0'*64)

    def test_bounds_and_hostile_inputs(self):
        package = self.first()
        for number in range(1, 16):
            package = self.add(package, number)
        self.assertEqual(len(package['revisions']), 16)
        self.refusal('REVISION_BOUNDS', self.add, package, 16)
        self.refusal('REVISION_BOUNDS', r.loads, b' '*1048577)
        self.refusal('REVISION_BOUNDS', r.loads, b'['*33+b']'*33)
        self.refusal('REVISION_JSON', r.loads, b'{"x":false,"x":false}')
        self.refusal('REVISION_UTF8', r.canonical, '\ud800')
        cycle = []; cycle.append(cycle)
        self.refusal('REVISION_SHAPE', r.canonical, cycle)
        self.refusal('REVISION_SHAPE', r.canonical, object())
        self.refusal('REVISION_BOUNDS', r.canonical, '\t'*600000)

    def test_pins_and_source(self):
        self.refusal('REVISION_SOURCE_PIN', r.initialize, source(0),
                     source_sha256='0'*64, program_sha256=program_pin(0))
        self.refusal('REVISION_PROGRAM_PIN', r.initialize, source(0),
                     source_sha256=sha(source(0)), program_sha256='0'*64)
        foreign = source(0).replace(b'form/5', b'form/6')
        self.refusal('REVISION_SOURCE', r.initialize, foreign,
                     source_sha256=sha(foreign), program_sha256=program_pin(0))

    def test_layout_noop_import_and_escaped_package_bound(self):
        first = self.first()
        layout = source(0) + b'\n'
        kw = dict(expected_package_sha256=sha(canonical(first)), expected_head=first['head'],
                  source_sha256=sha(layout), program_sha256=program_pin(0))
        self.refusal('REVISION_NO_CHANGE', r.append, first, layout, **kw)
        row = {'parent': first['head'], 'source_sha256': sha(layout),
               'program_sha256': program_pin(0)}
        row['id'] = sha(canonical(row))
        row['source'] = layout.decode()
        imported = copy.deepcopy(first)
        imported['revisions'].append(row); imported['head'] = row['id']
        self.refusal('REVISION_NO_CHANGE', r.loads, canonical(imported))
        before = canonical(first)
        large = source(1) + b'\t' * 525000
        self.assertLess(len(large), r.LIMIT)
        self.refusal('REVISION_BOUNDS', r.append, first, large,
            expected_package_sha256=sha(before), expected_head=first['head'],
            source_sha256=sha(large), program_sha256=program_pin(1))
        self.assertEqual(canonical(first), before)

    def test_cli_fresh_output_and_existing_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); src = root/'source'; out = root/'package'; dst = root/'checkout'
            src.write_bytes(source(0))
            args = ['init', str(src), '--output', str(out), '--source-sha256', sha(source(0)),
                    '--program-sha256', program_pin(0)]
            self.assertEqual(cli.main(args), 0)
            before = out.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(cli.main(args), 1)
            self.assertEqual(errors.getvalue(), 'RECORD_PATH\n')
            self.assertEqual(out.read_bytes(), before)
            package = json.loads(before)
            self.assertEqual(cli.main(['checkout', str(out), '--revision', package['head'],
                                      '--output', str(dst)]), 0)
            self.assertEqual(dst.read_bytes(), source(0))
            successor = root/'successor'; source_b = root/'source-b'; summary = root/'summary'
            source_b.write_bytes(source(1))
            self.assertEqual(cli.main(['append', str(out), '--source', str(source_b),
                '--output', str(successor), '--source-sha256', sha(source(1)),
                '--program-sha256', program_pin(1), '--package-sha256', sha(before),
                '--head', package['head']]), 0)
            self.assertEqual(cli.main(['inspect', str(successor), '--output', str(summary)]), 0)
            inspected = json.loads(summary.read_bytes())
            self.assertEqual(len(inspected['revisions']), 2)
            self.assertTrue(all('source' not in row for row in inspected['revisions']))
            self.assertEqual(out.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
