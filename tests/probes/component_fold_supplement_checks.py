from pathlib import Path
import json,hashlib,sys,subprocess,copy
T=Path(__file__).resolve().parents[2]
from outcome_host import configure
args=configure(reference=True);R=args.output;ref=args.reference;R.mkdir(exist_ok=False);sys.path.insert(0,str(T/'src'))
import bagaev_component_fold_form as form
import bagaev_component_text_list_form as prior
frozen=json.loads((T/'examples/probes/component-fold/cases.json').read_bytes());base=frozen['positive'][0]['source']
rows=[]
for name,expression,reason in [('zero-type','fold (0, 7) with (idx, acc) in true','RR_TYPE'),('scope','let idx = 2 in fold (1, 0) with (idx, acc) in acc','RR_SHAPE'),('seed-scope','fold (1, acc) with (idx, acc) in acc','RR_REFERENCE'),('overflow','fold (1, 9223372036854775807) with (idx, acc) in acc + 1','RR_OVERFLOW')]:
 source=base.replace('fold (0, 7) with (idx, acc) in acc + idx',expression);p=form.decode(source)['program'];p['entry']='calc';path=R/(name+'.json');path.write_text(json.dumps({'schema':'bagaev-typed-record-invocation/10','program':p,'arguments':[]}));q=subprocess.run([str(ref),'run','--input',str(path)],capture_output=True,timeout=20);(R/(name+'.stdout')).write_bytes(q.stdout);assert q.returncode==0 and not q.stderr;v=json.loads(q.stdout);assert v['reason']==reason,(name,v);rows.append({'id':name,'wire':v})
legacy=json.loads((T/'examples/probes/component-text-list/cases.json').read_bytes())
for case in legacy['positive']:
 assert prior.decode(case['source'])==case['expected'];assert form.decode(case['source'].replace('component-form/5','component-form/6'))==case['expected']
for codec,source in [(prior,base),(form,base.replace('component-form/6','component-form/5'))]:
 try:codec.decode(source)
 except form.FormError as e:assert e.code=='FORM_VERSION'
 else:raise AssertionError('version accepted')
result={'status':'PASSED','core_refusals':rows,'legacy_graphs':14,'version_refusals':2};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':'PASSED','core_refusals':4,'legacy_graphs':14,'version_refusals':2})
