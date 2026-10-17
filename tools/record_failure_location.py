#!/usr/bin/env python3
"""Locate a retained failure in explicit form5 source without executing it."""
import hashlib
import json
import sys
from record_text import Parser, Refusal, LIMIT, read_input, parse_json, write_output
from bagaev_record_draft import DraftError
from bagaev_record_wide_form import FormError
from bagaev_record_failure_location import locate_failure

SCHEMA = 'bagaev-record-failure-location-tool/1'


def create(argv):
    parser = Parser(add_help=False, allow_abbrev=False)
    parser.add_argument('source')
    parser.add_argument('capture')
    parser.add_argument('--form', choices=('5',), required=True)
    parser.add_argument('--program-sha256', required=True)
    parser.add_argument('--arguments-sha256', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    source = read_input(args.source)
    capture = read_input(args.capture)
    result = locate_failure(source, parse_json(capture),
                            program_sha256=args.program_sha256,
                            arguments_sha256=args.arguments_sha256,
                            source_sha256=args.source_sha256)
    result['capture_file_sha256'] = hashlib.sha256(capture).hexdigest()
    raw = json.dumps(result, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode('utf8')
    if len(raw) > LIMIT:
        raise Refusal('RECORD_BOUNDS')
    write_output(args.output, raw)
    return dict(output_bytes=len(raw), output_sha256=hashlib.sha256(raw).hexdigest(),
                semantic_check=False, capture_authentication=False,
                execution_admission=False)


def main(argv=None):
    try:
        result = create(sys.argv[1:] if argv is None else argv)
        receipt = dict(schema=SCHEMA, ok=True, result=result)
        code = 0
    except (Refusal, DraftError, FormError) as error:
        receipt = dict(schema=SCHEMA, ok=False, error=dict(code=error.code))
        code = 2
    print(json.dumps(receipt, sort_keys=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
