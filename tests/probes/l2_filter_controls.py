"""Own single-fault variants; no changed execution profile or external code."""
from pathlib import Path
import argparse,copy,hashlib,json,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter'
sys.path.insert(0,str(T))
from src import bagaev_l2_filter as genuine
from l2_filter_checks import program
enc=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()

def replace_once(text,before,after):
    assert text.count(before)==1,(before,text.count(before))
    return text.replace(before,after)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
    assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
    manifest=json.loads((D/'manifest.json').read_bytes())['sha256']
    assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
    controls=json.loads((D/'controls.json').read_bytes())['controls']
    cases={c['id']:c for c in json.loads((D/'cases.json').read_bytes())['cases']}
    core=(T/'src/bagaev_l2_filter.py').read_text();compiler=(T/'src/bagaev_l2_filter_backend.py').read_text()
    (R/'bagaev_l2_runtime.py').write_bytes((T/'src/bagaev_l2_runtime.py').read_bytes());rows=[]
    for i,control in enumerate(controls):
        engine,fault=control['engine'],control['fault'];text=core if engine=='reference' else compiler
        if engine=='reference':
            if fault=='append-predicate':text=replace_once(text,'accumulated.append(array[index - 1])','accumulated.append(result)')
            elif fault=='reverse':text=replace_once(text,'                    result = accumulated','                    result = list(reversed(accumulated)) if op == "filter" else accumulated')
            elif fault=='deduplicate':text=replace_once(text,'                    if result:\n                        accumulated.append(array[index - 1])','                    if result and array[index - 1] not in accumulated:\n                        accumulated.append(array[index - 1])')
            elif fault=='truthiness':text=replace_once(text,'                if op == "filter":\n                    _need(type(result) is bool, "L2_TYPE")','                if op == "filter":\n                    _need(type(result) in (bool, int), "L2_TYPE")')
            elif fault=='skip-last':text=replace_once(text,'            if index == len(array):','            if index == (len(array) - 1 if op == "filter" else len(array)):')
        else:
            if fault=='append-predicate':text=replace_once(text,'emit("answers.append(item)", 3)','emit("answers.append(answer)", 3)')
            elif fault=='reverse':text=replace_once(text,'emit("return answers")','emit("return list(reversed(answers))" if op == "filter" else "return answers")')
            elif fault=='truthiness':text=replace_once(text,'emit("if c.boolean(answer):", 2)','emit("if answer:", 2)')
            elif fault=='skip-last':text=replace_once(text,'emit("for item in items:")','emit("for item in items[:-1]:" if op == "filter" else "for item in items:")')
        path=R/f'{i:02d}-{engine}-{fault}.py';path.write_text(text)
        ns={'__name__':f'src.owned_filter_fault_{i}','__package__':'src','__file__':str(path)};exec(compile(text,str(path),'exec'),ns)
        case=cases[control['case']];source=program(['filter',['var','x'],'item',['get',['var','item'],'keep']]);arg=copy.deepcopy(case['input']);before=enc(arg)
        if engine=='reference':actual=ns['evaluate'](ns['check_program'](source),arg)
        else:
            checked=genuine.check_program(source);raw=ns['verify_artifact'](ns['compile_program'](checked),checked)
            child={'__name__':'owned_filter_fault_lowering'};exec(compile(raw,'<owned-filter-fault>','exec'),child);actual=child['evaluate'](arg)
        assert enc(actual)==enc(control['wrong']) and enc(arg)==before
        assert 'error'in case or enc(actual)!=enc(case['expected'])
        rows.append({'engine':engine,'fault':fault,'case':case['id'],'normal_wrong_value':actual,'mutant_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    result={'status':'PASSED','controls':rows,'count':len(rows),'scope':'Controlled normal wrong outputs, no independent reproduction or universal bug proof.'}
    (R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASSED','normal_wrong_controls':len(rows)}))

if __name__=='__main__':main()
