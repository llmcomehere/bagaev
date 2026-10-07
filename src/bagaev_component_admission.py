"""Pure finite five-obligation decision; matcher is a separately configured host dependency."""
import json
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def decide(graph,trusted,binding,observations,matcher,base,authority):
 def out(d,r):return {'decision':d,'reason':r}
 if enc(graph)!=enc(trusted):return out('invalid','requirements')
 if type(observations)is not list or len(observations)>10:return out('invalid','receipts')
 ids={o['id'] for o in trusted['obligations']};dims={'domain':{'artifact','request'},'subject':{'A','B'},'method':{'bytes','static','runtime'},'binding':{'fixture','consumer','detached'},'scope':{'partial','complete'}}
 for o in observations:
  if type(o)is not dict or set(o)!={'obligation','applicability','receipt'} or type(o['obligation'])is not str or o['obligation'] not in ids:return out('invalid','receipts')
  a=o['applicability'];v=o['receipt']
  if type(a)is not dict or set(a)!=set(binding) or any(type(x)is not str for x in a.values()):return out('invalid','receipts')
  if type(v)is not dict or set(v)!=set(dims)|{'revision','outcome','selected'}:return out('invalid','receipts')
  if any(type(v[k])is not str or v[k]not in values for k,values in dims.items()):return out('invalid','receipts')
  if type(v['revision'])is not int or not 0<=v['revision']<=2 or type(v['selected'])is not int or not 0<=v['selected']<=2:return out('invalid','receipts')
  if type(v['outcome'])is not str or v['outcome']not in {'pass','unknown','refuted','withdrawn'} or (v['method']!='runtime' and v['selected']!=0):return out('invalid','receipts')
 by_id={o['id']:o['requirement'] for o in trusted['obligations']}
 applicable=[o for o in observations if o['applicability']==binding and all(o['receipt'][k]==v for k,v in by_id[o['obligation']].items())];groups=[]
 for ids_in_group in trusted['groups']:
  req=[o['requirement'] for o in trusted['obligations'] if o['id'] in ids_in_group];receipts=[o['receipt'] for o in applicable if o['obligation'] in ids_in_group]
  if len(receipts)>4:return out('invalid','receipts')
  groups.append((req,receipts))
 # All wrappers/groups validated before any accepted group can matter.
 results=[matcher.group(q,r) for q,r in groups]
 if any(x['reason']=='conflicting-evidence' for x in results):return out('pending','conflicting-evidence')
 if any(x['decision']!='accepted' for x in results):return out('pending','missing-obligation')
 if base!=trusted['base_component_sha256']:return out('stale','base-changed')
 if authority is not True:return out('denied','admission-authority')
 return out('accepted','all-obligations')
