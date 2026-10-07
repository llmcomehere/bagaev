#!/usr/bin/env python3
"""Read bounded form/3 source and print diagnostics; never run the component."""
import argparse,json,sys
from component_text import Parser,Refusal,read_input
import bagaev_component_arithmetic_diagnostics as diagnostic
def main(argv=None):
 diag=diagnostic
 selected='3'
 try:
  parser=Parser(add_help=False,allow_abbrev=False);parser.add_argument('input');parser.add_argument('--form',choices=('3','4'),default='3')
  args=parser.parse_args(sys.argv[1:] if argv is None else argv)
  selected=args.form
  if selected=='4':
   import bagaev_component_match_diagnostics as diag
  result=diag.diagnose(read_input(args.input))
 except Refusal as error:
  result={'schema':diag.SCHEMA,'form':'component-form/'+selected,'valid_form':False,'source_sha256':None,'semantic_check':False,'execution_admission':False,'error':{'code':error.code,'phase':'transport','span':None}}
 print(json.dumps(result,sort_keys=True,separators=(',',':')))
 return 0 if result['valid_form'] else 2
if __name__=='__main__':raise SystemExit(main())
