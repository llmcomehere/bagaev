"""Bounded data-only replay: emit arguments or compare a full result. Never executes code."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]

def bounded(path,limit):
    with Path(path).open('rb') as stream:
        import os,stat
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:raise ValueError('file bound')
        data=stream.read(limit+1)
        if len(data)>limit:raise ValueError('file bound')
        return data

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['request','check','list'])
    parser.add_argument('case',nargs='?')
    parser.add_argument('--mode',choices=['reference','native'],default='reference')
    parser.add_argument('--output')
    a=parser.parse_args()
    data=json.loads(bounded(ROOT/'examples/probes/prepared-json/catalog-cases.json',4*1024*1024))
    if data['schema']!='prepared-catalog-replay/1':raise ValueError('schema')
    if data['source_file']!='examples/probes/catalog-source/program.json':raise ValueError('source path')
    source=bounded(ROOT/'examples/probes/catalog-source/program.json',1048576)
    if hashlib.sha256(source).hexdigest()!=data['source_sha256']:raise ValueError('source identity')
    cases={c['id']:c for c in data['cases']}
    if len(cases)!=103 or len(data['cases'])!=103:raise ValueError('fixture count')
    if a.action=='list':
        if a.case is not None or a.output is not None:raise ValueError('unexpected argument')
        print(json.dumps([{'id':c['id'],'work':c['work']} for c in data['cases']]));return
    if a.case not in cases:raise ValueError('unknown case')
    c=cases[a.case]
    if a.action=='request':
        if a.output is not None:raise ValueError('unexpected output')
        sys.stdout.buffer.write(bytes.fromhex(c['arguments_hex']));return
    if a.output is None:raise ValueError('output required')
    actual=bounded(a.output,4325440)
    if actual!=bytes.fromhex(c[a.mode+'_hex']):raise ValueError('complete output mismatch')
    print(json.dumps({'case':c['id'],'mode':a.mode,'complete_output_match':True,'work':c['work']}))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(str(e),file=sys.stderr);raise SystemExit(2)
