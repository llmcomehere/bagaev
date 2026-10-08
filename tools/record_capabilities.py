#!/usr/bin/env python3
"""Print source-profile discovery metadata; no file writes or execution."""
import json,sys
import record_text as transport
import bagaev_record_capabilities as capabilities

def main(argv=None):
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False)
        p.add_argument('--form',choices=('4','5'),required=True)
        p.add_argument('--revision',choices=('1','2','3','4'),default='1')
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        print(json.dumps(({'1':capabilities.describe,'2':capabilities.describe_v2,'3':capabilities.describe_v3,'4':capabilities.describe_v4}[a.revision](a.form)),sort_keys=True,separators=(',',':')))
        return 0
    except (transport.Refusal,capabilities.narrow.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-capabilities/1','error':{'code':e.code}},sort_keys=True,separators=(',',':')))
        return 2
if __name__=='__main__':raise SystemExit(main())
