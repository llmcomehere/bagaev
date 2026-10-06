"""Standalone data-only qualification for a partial descriptive build record."""
from pathlib import Path
import copy,hashlib,importlib.util,json,types
from build_record_fixtures import materialize
ROOT=Path(__file__).resolve().parents[2]
def main():
    d=ROOT/'examples/probes/build-record'
    spec=importlib.util.spec_from_file_location('build_record',d/'inspect_record.py')
    api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
    cases=json.loads((d/'cases.json').read_text());by_name={c['name']:c for c in cases}
    assert len(cases)==len(by_name)==42
    for case in cases:
        raw,expected,content=materialize(case);before=copy.deepcopy((expected,content))
        try:
            result=api.inspect(raw,expected,content)
            assert result=={'status':'matched-data','execution_admission':False,'build_verified':False,'dependencies_resolved':False}
            actual=result['status']
        except api.Refusal as e:actual=str(e)
        assert actual==case['expected'],(case['name'],actual)
        assert (expected,content)==before
    source=(d/'inspect_record.py').read_text();mutations=json.loads((d/'mutations.json').read_text())
    for m in mutations:
        assert source.count(m['old'])==m['occurrences']
        changed=source.replace(m['old'],m['new'],m['replacements']);mod=types.ModuleType(m['name']);exec(compile(changed,m['name'],'exec'),mod.__dict__)
        raw,expected,content=materialize(by_name[m['witness']]);result=mod.inspect(raw,expected,content)
        assert result['status']=='matched-data'
        if m['name']=='promote-build-assertion':assert result['build_verified'] is True
        else:assert by_name[m['witness']]['expected']!='matched-data'
    print(json.dumps({'status':'PASS','literal_cases':len(cases),'normal_wrong_controls':len(mutations),'native_calls':0,'builds':0}))
if __name__=='__main__':main()
