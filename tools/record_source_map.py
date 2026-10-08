#!/usr/bin/env python3
"""Explicit pinned form5 source mapping; data-only, never launches code."""
import hashlib
import json
import re
import sys
import record_text as transport
import bagaev_record_wide_spans as spans

SCHEMA = 'bagaev-record-source-map-receipt/1'


def create(argv):
    parser = transport.Parser(add_help=False, allow_abbrev=False)
    parser.add_argument('input')
    parser.add_argument('--form', choices=('5',), required=True)
    parser.add_argument('--program-pin', required=True)
    parser.add_argument('--source-sha256')
    parser.add_argument('--pointer')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', args.program_pin):
        raise transport.Refusal('SOURCE_MAP_PIN')
    if args.source_sha256 is not None and not re.fullmatch(r'[0-9a-f]{64}', args.source_sha256):
        raise transport.Refusal('SOURCE_MAP_LAYOUT')
    value = spans.source_map(transport.read_input(args.input))
    if value['program_pin'] != args.program_pin:
        raise transport.Refusal('SOURCE_MAP_PIN')
    if args.source_sha256 is not None and value['source_sha256'] != args.source_sha256:
        raise transport.Refusal('SOURCE_MAP_LAYOUT')
    if args.pointer is not None:
        selected = [item for item in value['locations'] if item['program_pointer'] == args.pointer]
        if len(selected) != 1:
            raise transport.Refusal('SOURCE_MAP_POINTER')
        value['locations'] = selected
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8')
    if len(data) > transport.LIMIT:
        raise transport.Refusal('RECORD_BOUNDS')
    transport.write_output(args.output, data)
    return dict(schema=SCHEMA, ok=True, program_pin=value['program_pin'],
                source_sha256=value['source_sha256'], output_sha256=hashlib.sha256(data).hexdigest(),
                location_count=len(value['locations']), semantic_check=False, execution_admission=False)


def main(argv=None):
    try:
        result = create(sys.argv[1:] if argv is None else argv)
        code = 0
    except (transport.Refusal, spans.form.FormError) as error:
        result = dict(schema=SCHEMA, ok=False, error=dict(code=error.code))
        code = 2
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
