"""Straightforward ordinary finite-graph baseline, with the same inventory premise."""
def decide(inventory):
 def out(d,r):return {'decision':d,'reason':r,'execution_admission':False}
 if not inventory['complete']:return out('unavailable','incomplete-inventory')
 nodes=inventory['nodes'];edges=inventory['edges'];ids=[n['id']['value'] for n in nodes]
 if len(ids)!=len(set(ids)) or any(not 1<=i<=4 for i in ids):return out('invalid','graph')
 if any(n['kind'] not in ('terminal','diagnostic','consumer','artifact') or n['phase'] not in ('live','planned','retired') or n['phase']=='planned' and n['retire'] or n['kind']=='terminal' and n['phase']=='retired' for n in nodes):return out('invalid','graph')
 pairs=[(e['consumer']['value'],e['witness']['value']) for e in edges]
 if len(pairs)!=len(set(pairs)) or any(a not in ids or b not in ids for a,b in pairs):return out('invalid','graph')
 if any(n['kind']=='terminal' and n['retire'] for n in nodes):return out('refused','terminal-retirement')
 by_id={n['id']['value']:n for n in nodes}
 for a,b in pairs:
  consumer,witness=by_id[a],by_id[b]
  if consumer['phase']=='live' and not consumer['retire'] and (witness['phase']!='live' or witness['retire']):return out('refused','live-dependency')
 for a,b in pairs:
  consumer,witness=by_id[a],by_id[b]
  if consumer['phase']=='planned' and (witness['phase'] not in ('live','planned') or witness['retire']):return out('refused','creation-dependency')
 # Ordinary DFS, deliberately distinct from the probe's bounded path expansion.
 visiting=set();done=set()
 def cycle(i):
  if i in visiting:return True
  if i in done:return False
  visiting.add(i)
  for a,b in pairs:
   if a==i and by_id[b]['phase']=='planned' and cycle(b):return True
  visiting.remove(i);done.add(i);return False
 if any(n['phase']=='planned' and cycle(n['id']['value']) for n in nodes):return out('refused','phase-cycle')
 return out('supported','finite-plan')
