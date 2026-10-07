#!/usr/bin/env python3
"""Read bounded form/3 source and print diagnostics; never run the component."""
import argparse,json,sys
from component_text import Parser,Refusal,read_input
import bagaev_component_arithmetic_diagnostics as diagnostic
def main(argv=None):
 try:
  parser=Parser(add_help=False,allow_abbrev=False);parser.add_argument('input')
  args=parser.parse_args(sys.argv[1:] if argv is None else argv)
  result=diagnostic.diagnose(read_input(args.input))
 except Refusal as error:
  result={'schema':diagnostic.SCHEMA,'form':'component-form/3','valid_form':False,'source_sha256':None,'semantic_check':False,'execution_admission':False,'error':{'code':error.code,'phase':'transport','span':None}}
 print(json.dumps(result,sort_keys=True,separators=(',',':')))
 return 0 if result['valid_form'] else 2
if __name__=='__main__':raise SystemExit(main())
