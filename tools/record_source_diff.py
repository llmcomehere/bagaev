"""Read-only comparison of two pinned form5 sources."""
import hashlib
import os
import sys
import record_text as transport
import bagaev_record_source_diff as diff

HELP = '''Compare two caller-pinned record-form/5 sources as data.
Usage: record_source_diff.py BEFORE AFTER --before-sha256 SHA256 --after-sha256 SHA256 --output NEW_REPORT
Reports source-byte and canonical-program differences, not semantic equivalence.
No semantic checking, execution, patch application or admission is performed.
Both equal and different comparisons return zero; inspect the report.
'''

def _write_stdout(raw, code):
    try:
        if os.write(1, raw) != len(raw):
            raise OSError('short delivery')
    except OSError:
        try:
            os.write(2, b'DIFF_DELIVERY\n')
        except OSError:
            pass
        return 1
    return code

def _envelope(value, code):
    return _write_stdout(diff._canonical(value) + b'\n', code)

def _read_side(path, side):
    try:
        return transport.read_input(path)
    except transport.Refusal as error:
        raise diff.DiffError(error.code, side) from None

def _preserved(paths, contents):
    for side, path, expected in zip(('before', 'after'), paths, contents):
        try:
            raw = _read_side(path, side)
        except diff.DiffError:
            raise diff.DiffError('DIFF_CHANGED', side) from None
        if raw != expected:
            raise diff.DiffError('DIFF_CHANGED', side)

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv in (['--help'], ['-h']):
        return _write_stdout(HELP.encode('utf-8'), 0)
    try:
        parser = transport.Parser(add_help=False, allow_abbrev=False)
        parser.add_argument('before'); parser.add_argument('after')
        parser.add_argument('--before-sha256', required=True)
        parser.add_argument('--after-sha256', required=True)
        parser.add_argument('--output', required=True)
        args = parser.parse_args(argv)
        diff._pins(args.before_sha256, args.after_sha256)
        before, after = _read_side(args.before, 'before'), _read_side(args.after, 'after')
        report = diff.compare_sources(before, after, before_sha256=args.before_sha256,
                                      after_sha256=args.after_sha256)
        raw = diff.encode_report(report)
        _preserved((args.before, args.after), (before, after))
        transport.write_output(args.output, raw)
        try:
            observed = transport.read_input(args.output)
        except transport.Refusal:
            raise diff.DiffError('DIFF_OUTPUT') from None
        if observed != raw:
            raise diff.DiffError('DIFF_OUTPUT')
        _preserved((args.before, args.after), (before, after))
        return _envelope({'schema': 'bagaev-record-diff-tool/1', 'ok': True,
                          'result': {'output_bytes': len(raw), 'output_sha256': hashlib.sha256(raw).hexdigest()}}, 0)
    except (transport.Refusal, diff.DiffError) as error:
        return _envelope({'schema': 'bagaev-record-diff-tool/1', 'ok': False,
                          'error': {'code': error.code, 'side': getattr(error, 'side', None)}}, 2)

if __name__ == '__main__':
    raise SystemExit(main())
