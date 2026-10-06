"""Owned finite admission bridge using exact prior qualified observations."""
import component_change as q
import sys
import component_cycle as c
b=c.b
def main():
 parser=q.argparse.ArgumentParser(description='Connected simulated change with retained source-bound qualification.')
 parser.add_argument('--matcher',required=True);parser.add_argument('--matcher-sha256',required=True)
 ns,remaining=parser.parse_known_args();original_args=sys.argv;sys.argv=[sys.argv[0],*remaining]
 try:c.configure()
 finally:sys.argv=original_args
 root=b.R;matcher_dir=root/'matcher';application=root/'application';application.mkdir();b.R=application
 q.configure(['--matcher',ns.matcher,'--matcher-sha256',ns.matcher_sha256,'--output',str(matcher_dir)])
 graph,binding,observations,cache=q.verify_cache();m=q.Matcher(q.MATCHER,q.MATCHER_SHA);c.verify_component_inputs();b.verify_inputs()
 expected=q.read(q.D/'connected-expectations.json');b.need(q.sha((b.D/'cases.json').read_bytes())==expected['whole_cycle_cases_sha256'],'connected oracle pin')
 engine=c.ComponentEngine();decisions=[]
 class Receiver(b.Receiver):
  def execute(self,e):
   if e['command']!='AdmitProgramme':return super().execute(e)
   before=b.clone((self.state,self.ledger,self.runs))
   if e['requires_migration']:self.last='UnsupportedMigration';return
   b.need(e['candidate']=='S2' and e['obligation_set']=='catalogue-contract/v1','unsupported change')
   evidence=b.clone(observations)
   if e['evidence_set']=='missing-actual-entry-consumer':evidence=[o for o in evidence if o['obligation']!='actual-entry-consumer']
   else:b.need(e['evidence_set']=='complete-admissible-fixture','unknown evidence selection')
   base=graph['base_component_sha256'] if self.default==e['base']=='S1' else '0'*64
   decision=q.decide(graph,graph,binding,evidence,m,base,e['admission_authorized'])
   if getattr(self,'inject_head_change_after_check',False):self.default='S2'
   if decision['decision']=='accepted' and self.default!=e['base']:decision={'decision':'stale','reason':'base-changed'}
   decisions.append({'case':self.current_case,'decision':decision,'prior_qualification_at':cache['original_execution_at']})
   if decision['decision']=='accepted':self.default='S2';self.last='SimulatedAdmissionAccepted'
   elif decision['decision']=='denied':self.last='AccessDenied'
   elif decision['decision']=='stale':self.last='AdmissionStale'
   elif decision['decision']=='pending':self.last='AdmissionUnresolved';self.extra['missing_obligation']='actual-entry-consumer'
   else:raise ValueError('invalid trusted admission input')
   b.need((self.state,self.ledger,self.runs)==before,'admission modified live state or old pins')
 suite=q.read(b.D/'cases.json');rows=[]
 for case in suite['cases']:
  receiver=Receiver(suite['profile'],engine);receiver.current_case=case['id'];start=len(engine.bindings)
  for event in case['events']:receiver.execute(event)
  actual=receiver.projection();diff={k:{'expected':v,'actual':actual.get(k)} for k,v in case['expected'].items() if b.encoded(v)!=b.encoded(actual.get(k))}
  if case['id']=='WC17':
   effects=engine.bindings[start:];b.need([x['source'] for x in effects]==['S1','S2'] and [x['operation_key']['id'] for x in effects]==['A','B'],'new application association')
  rows.append({'id':case['id'],'matched':not diff,'differences':diff,'actual':actual})
 before_calls=engine.count;receiver=Receiver(suite['profile'],engine);receiver.inject_head_change_after_check=True;receiver.current_case='final-boundary-control'
 event=next(e for case in suite['cases'] if case['id']=='WC17' for e in case['events'] if e['command']=='AdmitProgramme');receiver.execute(event)
 boundary={'last_observation':receiver.last,'default':receiver.default,'application_mutations':receiver.mutations,'ledger_rows':len(receiver.ledger),'old_run':receiver.runs['original']}
 b.need(boundary==q.read(q.D/'final-boundary-control.json')['expected'] and engine.count==before_calls,'final boundary control')
 result={'at':q.datetime.datetime.now(q.datetime.timezone.utc).isoformat(),'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','rows':rows,'final_boundary_control':boundary,'decisions':decisions,'prior_qualification':cache,'new_application_calls':engine.calls,'new_matcher_calls':m.calls,'scope':'Source-bound retained evidence drives simulated admission; prior qualification is not reexecuted. No production authority/durability.'}
 (q.R.parent/'result.json').write_text(q.json.dumps(result,indent=2)+'\n');print(q.json.dumps({'status':result['status'],'matched':sum(x['matched'] for x in rows),'requested':len(rows),'new_application_calls':engine.count,'new_matcher_calls':len(m.calls)}));b.need(result['status']=='PASSED','connected mismatch')
if __name__=='__main__':main()
