"""Bounded source-check CLI qualification; never execute a submitted program."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
import argparse

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description='Requires separately reviewed executable and execution authority.')
parser.add_argument('--checker', required=True, type=Path)
parser.add_argument('--checker-sha256', required=True)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
binary = args.checker.resolve()
out = args.output.resolve()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
assert binary.is_file() and binary.stat().st_size <= 33554432
binary_pin = sha(binary.read_bytes())
assert binary_pin == args.checker_sha256
out.mkdir(exist_ok=False)

def run(args, name, expected_exit=0):
    result = subprocess.run(list(map(str, args)),
                            capture_output=True, timeout=90)
    for suffix, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
        with (out/(name+'.'+suffix)).open('xb') as stream:
            stream.write(data)
    assert result.returncode == expected_exit, (name, result.returncode, result.stderr[-2000:])
    if expected_exit:
        assert result.stderr and not result.stdout
    elif name != 'build':
        assert not result.stderr
    return result.stdout

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()

base = {'schema':'bagaev-typed-record/11', 'records':{}, 'lists':{}, 'variants':{},
        'entry':'main', 'functions':{'main':{'params':[], 'result':'Int64','body':['int',0]}}}
cases = []
def add(name, value, reason=None, location=None, pin=None):
    raw = value if type(value) is bytes else canonical(value)
    cases.append((name, raw, {'execution_admission':False,
        'schema':'bagaev-record-source-check/11','status':'refused' if reason else 'checked',
        'program_sha256':None if reason else (pin or sha(canonical(value))),
        'reason':reason,'location':location,'input_sha256':sha(raw) if len(raw)<=1048576 else None}))

add('scalar', base)
add('scalar-whitespace', b' '+canonical(base)+b'\n', pin=sha(canonical(base)))
changed=copy.deepcopy(base);changed['functions']['main']['body']=['int',1]
add('scalar-changed', changed)
overflow = copy.deepcopy(base); overflow['functions']['main']['body']=['add',['int',9223372036854775807],['int',1]]
add('well-typed-overflow', overflow)
bad = copy.deepcopy(base); bad['functions']['main']['body']=['bool',True]
add('main-type', bad, 'RR_TYPE', '/functions/main/body')
bad = copy.deepcopy(base); bad['functions']['bad']={'params':[],'result':'Int64','body':['bool',True]}
add('unused-type', bad, 'RR_TYPE', '/functions/bad/body')
bad = copy.deepcopy(base); bad['functions']['main']['body']=['call','missing']
add('missing-call', bad, 'RR_REFERENCE', '/functions/main/body')
bad = copy.deepcopy(base); bad['schema']='bagaev-typed-record/10'
add('foreign-profile', bad, 'RR_VERSION', '/schema')
bad = copy.deepcopy(base); bad['extra']=False
add('extra-field', bad, 'RR_SHAPE', '')
add('malformed', b'{', 'RR_JSON', '')
add('oversized', b' '*1048577, 'RR_BOUNDS', '')

# Pure existing decoder only; expected program identities were frozen previously.
sys.path.insert(0, str(root/'src'))
import bagaev_record_wide_form as form
for name, path, expected in [
 ('inventory-original','inventory-reserve/Reserve.bagaev','753f14412252805ee3eeae9c2a659d076922c28fd12f316cee57654677db8c6a'),
 ('inventory-limited','inventory-change/ReserveLimited.bagaev','c403f4e482ee607dab12737dc66befef015f4499ffafd58ef75329362a20a915')]:
    source = root/'examples/probes'/path
    raw = source.read_bytes()
    program = form.decode(raw)
    assert sha(canonical(program)) == expected
    add(name, program, pin=expected)
    assert source.read_bytes() == raw

rows=[]
for name, raw, expected in cases:
    path=out/(name+'.json')
    with path.open('xb') as stream: stream.write(raw)
    actual=run([binary,'check','--input',path], name)
    assert actual == canonical(expected)+b'\n', (name,actual,expected)
    assert path.read_bytes() == raw and sha(binary.read_bytes()) == binary_pin
    rows.append({'case':name,'status':'PASS','input_sha256':sha(raw)})
run([binary], 'usage', expected_exit=1)
run([binary,'check','--input',out/'absent.json'], 'missing-input', expected_exit=1)
result={'status':'PASS','cases':rows,'binary_sha256':binary_pin,
        'source_program_evaluations':0,'checker_cli_calls':len(cases), 'usage_io_controls':2}
with (out/'evidence.json').open('x') as stream: json.dump(result,stream,indent=2)
print(json.dumps(result))
