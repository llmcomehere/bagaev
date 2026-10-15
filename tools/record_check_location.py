#!/usr/bin/env python3
"""Map retained source-check data; no subprocess or evaluation."""
import json
import sys
import record_text as transport
import bagaev_record_check_location as location
from bagaev_record_draft import DraftError


def main(argv=None):
    try:
        parser=transport.Parser(add_help=False,allow_abbrev=False)
        parser.add_argument('source')
        for name in ('checked-input','result','source-sha256','program-sha256',
                     'input-sha256','result-sha256','output'):
            parser.add_argument('--'+name,required=True)
        args=parser.parse_args(argv)
        result=location.locate(transport.read_input(args.source),
            transport.read_input(args.checked_input),transport.read_input(args.result),
            source_sha256=args.source_sha256,program_sha256=args.program_sha256,
            input_sha256=args.input_sha256,result_sha256=args.result_sha256)
        transport.write_output(args.output,json.dumps(result,sort_keys=True,
            ensure_ascii=False,separators=(',',':')).encode('utf8'))
        return 0
    except (transport.Refusal,DraftError,location.form.FormError) as error:
        print(error.code,file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
