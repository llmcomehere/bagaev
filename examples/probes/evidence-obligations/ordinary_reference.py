"""Independent ordinary pure implementation of the fixed obligation contract."""
D=('domain','subject','revision','method','binding','scope')
E={'domain':{'artifact','request'},'subject':{'A','B'},'method':{'bytes','static','runtime'},'binding':{'fixture','consumer','detached'},'scope':{'partial','complete'}}
def common(x):
 return type(x) is dict and all(type(x.get(k)) is str and x[k] in v for k,v in E.items()) and type(x.get('revision')) is int and 0<=x['revision']<=2
def evaluate(qs,rs):
 def out(d,r):return {'decision':d,'reason':r}
 if type(qs) is not list or not 1<=len(qs)<=2:return out('invalid','requirements')
 if any(not common(q) or set(q)!=set(D) or q['scope']!='complete' for q in qs):return out('invalid','requirements')
 if len({tuple(q[k] for k in D) for q in qs})!=len(qs):return out('invalid','requirements')
 if type(rs) is not list or len(rs)>4:return out('invalid','receipts')
 for r in rs:
  if not common(r) or set(r)!=set(D)|{'outcome','selected'} or type(r.get('outcome')) is not str or r['outcome'] not in {'pass','unknown','refuted','withdrawn'} or type(r.get('selected')) is not int or not 0<=r['selected']<=2 or (r['method']!='runtime' and r['selected']!=0):return out('invalid','receipts')
 flags=[]
 for q in qs:
  exact=[r for r in rs if all(r[k]==q[k] for k in D)]
  passed=any(r['outcome']=='pass' and (r['method']!='runtime' or r['selected']>0) for r in exact)
  conflict=passed and any(r['outcome'] in {'refuted','withdrawn'} for r in exact)
  flags.append((passed,conflict))
 if any(c for _,c in flags):return out('pending','conflicting-evidence')
 return out('accepted','all-obligations') if all(p for p,_ in flags) else out('pending','missing-obligation')
