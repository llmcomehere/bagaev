#!/usr/bin/env python3
"""Locate a pinned form4 expression; never run or typecheck a component."""
import json
import sys
from component_text import Parser, Refusal, read_input
import bagaev_component_expression_locations as locations
import bagaev_component_match_form as form

def main(argv=None):
    try:
        parser = Parser(add_help=False, allow_abbrev=False)
        parser.add_argument('input')
        parser.add_argument('pointer')
        parser.add_argument('--source-sha256', required=True)
        parser.add_argument('--component-sha256', required=True)
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        result = locations.locate(read_input(args.input), args.pointer,
                                  source_sha256=args.source_sha256,
                                  component_sha256=args.component_sha256)
        code = 0
    except (Refusal, form.FormError, locations.LocationError) as error:
        result = {'schema': locations.SCHEMA, 'form': 'component-form/4',
                  'error': {'code': error.code}, 'semantic_check': False,
                  'execution_admission': False}
        code = 2
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
