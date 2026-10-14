"""Supplemental sender identity checks against unchanged frozen receipt fixtures."""
from copy import deepcopy
import hashlib, json
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.p0_sender import Sender
from src.p0_receiver import Receiver

class SenderTests(unittest.TestCase):
    def setUp(self):
        hashes={'p0.md':'30cb2b27a3011db96b6ce56e2c441fd04d2532baae0ff1649d1f64626edcbc5a',
                'p0-cases.json':'27b67c6e65c184cbd9f553b863d302f70300da6393d59c39e8e5c0241da6c1af'}
        for name,digest in hashes.items():
            self.assertEqual(hashlib.sha256((ROOT/'docs'/name).read_bytes()).hexdigest(),digest)
        self.fixtures=json.loads((ROOT/'docs/p0-cases.json').read_bytes())['fixtures']

    def fixture(self,name):
        def resolve(value):
            if type(value) is dict:
                if set(value)=={'$ref'}: return resolve(self.fixtures[value['$ref']])
                return {k:resolve(v) for k,v in value.items()}
            if type(value) is list: return [resolve(v) for v in value]
            return deepcopy(value)
        return resolve(self.fixtures[name])

    def refuse(self,sender,error,fn):
        before=sender.snapshot()
        with self.assertRaisesRegex(ValueError,'^'+error+'$'):fn()
        self.assertEqual(sender.snapshot(),before)

    def prepare(self,sender,kind='write',session=None,epoch=None):
        if session is None:session='session-writer-a' if kind=='write' else 'session-coordinator'
        if kind=='write' and epoch is None:epoch=4
        return sender.prepare(kind,'task-catalog','effect-a',session,epoch)

    def send(self,receiver,kind,request):
        return receiver.command(kind,request['session'],request['intent'],request.get('presented_epoch'))

    def test_save_identity_detachment_and_namespaces(self):
        s=Sender(); original=self.fixture('write-intent-k')
        self.refuse(s,'SENDER_UNSAVED',lambda:self.prepare(s))
        s.save('write','effect-a',original); expected=s.snapshot()
        s.save('write','effect-a',original);self.assertEqual(s.snapshot(),expected)
        original['mutation']['add'].append('red')
        request=self.prepare(s);self.assertEqual(request['intent'],self.fixture('write-intent-k'))
        request['intent']['mutation']['add'].append('red')
        snapshot=s.snapshot()
        snapshot['rows'][('write','task-catalog','effect-a')]['mutation']['add'].append('red')
        snapshot['ids'][('write','task-catalog','operation-k')]='changed-handle'
        self.assertEqual(s.snapshot(),expected)
        for field,value in [('operation_id','new-id'),('task_revision',8)]:
            intent=self.fixture('write-intent-k');intent[field]=value
            self.refuse(s,'SENDER_HANDLE_CONFLICT',lambda:s.save('write','effect-a',intent))
        self.refuse(s,'SENDER_ID_CONFLICT',lambda:s.save('write','other-effect',self.fixture('write-intent-k')))
        other=self.fixture('write-intent-k');other['task_id']='other-task'
        s.save('write','effect-a',other)
        transfer=self.fixture('transfer-intent-t1');transfer['transfer_id']='operation-k'
        s.save('transfer','effect-a',transfer)
        self.assertEqual(len(s.snapshot()['rows']),3);self.assertEqual(len(s.snapshot()['ids']),3)

    def test_synthetic_cuts_restore_both_indexes(self):
        for commit in (False,True):
            with self.subTest(commit=commit):
                s=Sender();s.save('write','prior',self.fixture('write-intent-m'));prior=s.snapshot()
                if commit:s.save('write','effect-a',self.fixture('write-intent-k'))
                saved=s.snapshot();s.crash()
                self.refuse(s,'SENDER_REQUIRES_RECOVERY',lambda:self.prepare(s))
                self.refuse(s,'SENDER_REQUIRES_RECOVERY',lambda:s.save('write','effect-a',self.fixture('write-intent-k')))
                s.recover();self.assertEqual(s.snapshot(),saved)
                for index in ('rows','ids'):
                    for key,value in prior[index].items():self.assertEqual(saved[index][key],value)
                self.refuse(s,'SENDER_NOT_CRASHED',s.recover)
                if commit:
                    self.assertEqual(self.prepare(s)['intent'],self.fixture('write-intent-k'))
                    changed=self.fixture('write-intent-k');changed['operation_id']='new-id'
                    self.refuse(s,'SENDER_HANDLE_CONFLICT',lambda:s.save('write','effect-a',changed))
                    self.refuse(s,'SENDER_ID_CONFLICT',lambda:s.save('write','other',self.fixture('write-intent-k')))
                else:
                    self.assertEqual(saved,prior)
                    self.refuse(s,'SENDER_UNSAVED',lambda:self.prepare(s))
                    s.save('write','effect-a',self.fixture('write-intent-k'))

    def test_lost_reply_retry_and_current_authority(self):
        for kind in ('write','transfer'):
            with self.subTest(kind=kind):
                s=Sender();s.save(kind,'effect-a',self.fixture(kind+'-intent-'+('k' if kind=='write' else 't1')))
                r=Receiver(self.fixture('protocol-base'),self.fixture('sessions'))
                initial=self.send(r,kind,self.prepare(s,kind))
                frozen=self.fixture(kind+'-receipt-'+('k' if kind=='write' else 't1'))
                self.assertEqual(initial['response']['value'],frozen)
                committed=r.snapshot();saved=s.snapshot()
                # Drop the reply; sender has no observation-derived mutation or fresh ID.
                s.crash();s.recover()
                retry=self.send(r,kind,self.prepare(s,kind))
                self.assertEqual(retry['response']['value'],frozen)
                self.assertEqual(r.snapshot(),committed);self.assertEqual(s.snapshot(),saved)
                if kind=='write':
                    r.command('transfer','session-coordinator',self.fixture('transfer-intent-t1'))
                    refused=self.send(r,kind,self.prepare(s,kind))
                    self.assertEqual(refused['response'],{'kind':'current-refusal','reason':'assignee-mismatch'})
                    self.assertFalse(refused['receipt_lookup_performed'])
                    after_transfer=r.snapshot()
                    successor=self.send(r,kind,self.prepare(s,kind,'session-writer-b',5))
                    self.assertEqual(successor['response']['value'],frozen)
                    self.assertEqual(r.snapshot(),after_transfer)
                else:
                    r.fixture_revoke('coordinator','manage:transfer')
                    refused=self.send(r,kind,self.prepare(s,kind))
                    self.assertEqual(refused['response'],{'kind':'current-refusal','reason':'transfer-scope-required'})
                    self.assertFalse(refused['receipt_lookup_performed'])
                self.assertEqual(s.snapshot(),saved)

    def test_absence_invalid_structure_and_semantic_boundary(self):
        s=Sender();bad=self.fixture('write-intent-k');del bad['operation_id']
        self.refuse(s,'SENDER_INVALID_INTENT',lambda:s.save('write','effect-a',bad))
        s.save('write','effect-a',self.fixture('write-intent-k'));saved=s.snapshot()
        r=Receiver(self.fixture('protocol-base'),self.fixture('sessions'))
        absent=r.command('query_operation','session-writer-a',task_id='task-catalog',receipt_id='operation-k')
        self.assertEqual(absent['response']['kind'],'receipt-absent-at-query')
        self.assertEqual(s.snapshot(),saved)
        self.refuse(s,'SENDER_INVALID_CONTEXT',lambda:self.prepare(s,epoch=True))
        self.refuse(s,'SENDER_INVALID_CONTEXT',lambda:self.prepare(s,session=1))
        self.refuse(s,'SENDER_INVALID_CONTEXT',lambda:s.prepare('transfer','task-catalog','effect-a','session-coordinator',4))
        invalid_tag=self.fixture('write-intent-m');invalid_tag['mutation']['add']=['BAD']
        s.save('write','invalid-tag',invalid_tag)
        request=s.prepare('write','task-catalog','invalid-tag','session-writer-a',4)
        result=self.send(r,'write',request)
        self.assertEqual(result['response']['outcome']['detail'],'invalid-tag')
        self.assertTrue(result['committed'])

if __name__=='__main__':unittest.main()
