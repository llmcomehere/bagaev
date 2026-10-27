#!/usr/bin/env python3
"""Детерминированные C02/C03/C07/C09/C13 для A/B/C; ни одного вызова LLM."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / 'pilot/authorship'
sys.path.insert(0, str(ROOT / 'ref'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import git_accept
from bagaev_ref.protocol.ops import Ops, PROTOCOL, init_project
from bagaev_ref.change.workstate import work_row


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load('mechanism_oracle', PILOT / 'oracle/run.py')
mutants = load('mechanism_mutants', PILOT / 'oracle/mutants.py')
CASES = ('C02', 'C03', 'C07', 'C09', 'C13')
CHECKS = {'C02': ('invalid-empty_authors', 'invalid-duplicate_author', 'invalid-unknown_person'),
          'C03': ('coauthor-not-editor',), 'C13': ('redelivery-deduplicated',)}


def req(op, label, ch=None, revision=None, **arguments):
    request = {'protocol': PROTOCOL, 'operation': op, 'arguments': arguments}
    if ch is not None:
        request['change_id'] = ch
    if revision is not None:
        request['expected_work_revision'] = revision
    if op in ('change_begin', 'apply', 'verify', 'accept'):
        request['idempotency_key'] = 'mechanism-' + hashlib.sha256((op + label).encode()).hexdigest()[:24]
    return request


def succeeded(result):
    if result.get('status') != 'succeeded':
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def byline(arm):
    if arm == 'C':
        return 'blog/byline.bag', 'people.display_name(all_people, a.author)', ' ++ ""'
    return 'src/byline.ts', 'return displayName(all, a.author)', ' + ""'


def validate_ts(app):
    tsc = ROOT / 'pilot/writability/node_modules/typescript/bin/tsc'
    for args in (["node", str(tsc), '-p', str(app / 'tsconfig.json')],
                 ['node', '--no-warnings', '--test', *map(str, sorted((app / 'test').glob('*.test.ts')))]):
        result = subprocess.run(args, capture_output=True, text=True, timeout=600)
        if result.returncode:
            raise RuntimeError((result.stdout + result.stderr)[-1500:])


def stale_git(baseline, tmp):
    initial, first, winner = (tmp / name for name in ('initial', 'first', 'winner'))
    for target in (initial, first, winner):
        shutil.copytree(baseline, target)
    rel, old, suffix = byline('A')
    for n, app in enumerate((first, winner), 1):
        file = app / rel
        text = file.read_text(encoding='utf-8')
        if text.count(old) != 1:
            raise RuntimeError('C07: baseline byline differs')
        file.write_text(text.replace(old, old + suffix * n), encoding='utf-8')
        validate_ts(app)
    state = tmp / 'acceptance'
    base = git_accept.init(initial, state)
    fresh = git_accept.accept(winner, state, base)
    stale = git_accept.accept(first, state, base)
    current = git_accept.head(state)
    return {'fresh': fresh, 'stale': stale, 'base': base, 'current': current,
            'ok': fresh['status'] == 'accepted' and fresh['head'] != base
                  and stale.get('code') == 'STALE_BASE' and current == fresh['head'],
            'method': 'tsc + node:test, Git update-ref CAS'}


def stale_protocol(arm, baseline, tmp):
    app = tmp / 'project'
    shutil.copytree(baseline, app)
    initial = init_project(app, 'mechanism')
    ops = Ops(app, 'mechanism')
    try:
        changes = []
        rel, old, suffix = byline(arm)
        for n in (1, 2):
            label = f'{arm}-{n}'
            begin = succeeded(ops.call(req('change_begin', label, intent='C07: эквивалентная правка подписи')))
            ch = begin['change_id']
            files = ops.store.files(work_row(ops.store, ch)['candidate'])
            raw = files[rel]
            if raw.decode().count(old) != 1:
                raise RuntimeError('C07: baseline byline differs')
            edit = {'files': [{'path': rel, 'base_sha256': hashlib.sha256(raw).hexdigest(),
                              'edits': [{'old_text': old, 'text': old + suffix * n}]}]}
            applied = succeeded(ops.call(req('apply', label, ch, begin['work_revision'], source_edit=edit)))
            verified = succeeded(ops.call(req('verify', label, ch, applied['work_revision'])))
            view = succeeded(ops.call(req('work_resume', label, ch)))['result']
            if not view['ready_for_acceptance']:
                raise RuntimeError('C07 candidate is not prepared: ' + json.dumps(view['blockers']))
            changes.append((ch, verified['work_revision'], label))
        ch, rev, label = changes[1]
        fresh = succeeded(ops.call(req('accept', label, ch, rev)))
        count = ops.store.db.execute('SELECT count(*) FROM acceptance').fetchone()[0]
        ch, rev, label = changes[0]
        stale = ops.call(req('accept', label, ch, rev))
        current = ops.store.meta('head')
        after = ops.store.db.execute('SELECT count(*) FROM acceptance').fetchone()[0]
        return {'fresh': fresh['result'], 'stale': stale, 'base': initial['head'], 'current': current,
                'acceptance_count_before': count, 'acceptance_count_after': after,
                'ok': stale.get('error', {}).get('code') == 'STALE_BASE'
                      and current == fresh['result']['head'] != initial['head'] and count == after,
                'method': 'CHANGE-1 verify/accept CAS, B and C same engine'}
    finally:
        ops.close()


def run_arm(arm):
    spec = json.loads((PILOT / 'arms.json').read_text(encoding='utf-8'))['arms'][arm]
    baseline, reference = ROOT / spec['baseline'], ROOT / spec['reference']
    positive = oracle.run(arm)
    observed = {row['id']: row for row in positive['checks']}
    checks = []
    for case, ids in CHECKS.items():
        ok = positive['outcome'] == 'PASS' and all(observed.get(cid, {}).get('outcome') == 'PASS' for cid in ids)
        checks.append({'case': case, 'outcome': 'PASS' if ok else 'FAIL', 'oracle_checks': list(ids)})
    with tempfile.TemporaryDirectory(prefix='bagaev-mechanism-') as tmp:
        tmp = Path(tmp)
        injected = mutants.inject(arm, 'index_not_updated', reference, tmp / 'stale-index')
        negative = oracle.run(arm, candidate=tmp / 'stale-index')
        detected = bool(set(negative['failed']) & {'state-d3-after-delivery', 'search-p_boris'})
        ok = positive['outcome'] == 'PASS' and negative['passed'] > 0 and detected
        checks.append({'case': 'C09', 'outcome': 'PASS' if ok else 'FAIL', 'injection': injected,
                       'failed_oracle_checks': negative['failed'], 'transition_verdict': 'REJECT' if detected else 'UNKNOWN',
                       'basis': 'Независимый oracle наблюдает состояние и поиск после завершённой доставки; не gate accept.'})
        evidence = stale_git(baseline, tmp) if arm == 'A' else stale_protocol(arm, baseline, tmp)
        checks.append({'case': 'C07', 'outcome': 'PASS' if evidence['ok'] else 'FAIL', 'evidence': evidence})
    checks.sort(key=lambda c: c['case'])
    return {'outcome': 'PASS' if all(c['outcome'] == 'PASS' for c in checks) else 'FAIL', 'checks': checks,
            'positive_oracle': {'outcome': positive['outcome'], 'passed': positive['passed'], 'total': positive['total']}}


def run(arms):
    results = {}
    for arm in arms:
        if arm in ('A', 'B') and (shutil.which('node') is None or not
                (ROOT / 'pilot/writability/node_modules/typescript/bin/tsc').is_file()):
            results[arm] = {'outcome': 'SKIP', 'reason': 'нет локального Node/TypeScript', 'checks': []}
            continue
        try:
            results[arm] = run_arm(arm)
        except Exception as exc:
            results[arm] = {'outcome': 'ERROR', 'reason': f'{type(exc).__name__}: {exc}', 'checks': []}
    states = {r['outcome'] for r in results.values()}
    outcome = 'FAIL' if states & {'FAIL', 'ERROR'} else 'INCOMPLETE' if 'SKIP' in states else 'PASS'
    return {'format': 'bagaev-mechanism/1', 'outcome': outcome, 'llm_calls': 0, 'pilot_status': 'NOT_RUN',
            'passed': sum(c['outcome'] == 'PASS' for r in results.values() for c in r['checks']),
            'total': len(arms) * len(CASES), 'arms': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', action='append', choices=['A', 'B', 'C'])
    args = parser.parse_args()
    report = run(list(dict.fromkeys(args.arm or ['A', 'B', 'C'])))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return {'PASS': 0, 'FAIL': 1, 'INCOMPLETE': 2}[report['outcome']]


if __name__ == '__main__':
    sys.exit(main())
