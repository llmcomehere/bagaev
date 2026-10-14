"""Frozen supplemental ingress checks; expectations do not come from the adapter."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import sys,unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.p0_receiver import Receiver
from src.p0_ingress import deliver

class ObservedReceiver(Receiver):
    def __init__(self, *args):
        super().__init__(*args); self.calls = 0
    def command(self, *args, **kwargs):
        self.calls += 1
        return super().command(*args, **kwargs)

class IngressTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT/'examples/probes/p0-json-ingress.json').read_bytes())
        for name, digest in self.plan['oracle_hashes'].items():
            self.assertEqual(hashlib.sha256((ROOT/'docs'/name).read_bytes()).hexdigest(), digest)
        self.fixtures = json.loads((ROOT/'docs/p0-cases.json').read_bytes())['fixtures']

    def fixture(self, name):
        def resolve(value):
            if type(value) is dict:
                if set(value) == {'$ref'}: return resolve(self.fixtures[value['$ref']])
                return {k:resolve(v) for k,v in value.items()}
            if type(value) is list: return [resolve(v) for v in value]
            return deepcopy(value)
        return resolve(self.fixtures[name])

    def receiver(self):
        return ObservedReceiver(self.fixture(self.plan['initial']), self.fixture('sessions'))

    def envelope(self, kind='write'):
        value = {'session':'session-writer-a' if kind == 'write' else 'session-coordinator',
                 'intent':self.fixture(self.plan[kind+'_intent'])}
        if kind == 'write': value['presented_epoch'] = 4
        return value

    @staticmethod
    def wire(value): return json.dumps(value,separators=(',',':')).encode()

    def refusal(self, kind, raw, category='request-refusal', reason='invalid-request'):
        receiver = self.receiver(); before = receiver.snapshot()
        result = deliver(receiver,kind,raw)
        self.assertEqual(result['response'], {'kind':category,'reason':reason})
        self.assertEqual(receiver.calls,0)
        self.assertEqual(receiver.snapshot(),before)
        for key in ('committed','receipt_lookup_performed','state_changed'):
            self.assertIs(result[key],False)
        result['record']['tags'].append('changed-observation')
        self.assertEqual(receiver.snapshot(),before)

    def test_malformed_before_dispatch(self):
        cases = {'truncated':('write',b'{"session":'), 'invalid-utf8':('write',b'\xff'),
                 'array-envelope':('write',b'[]'), 'nonfinite':('write',b'{"value":NaN}')}
        for name in self.plan['pre_dispatch_invalid']:
            if name in cases: continue
            kind = 'transfer' if name in ('unordered-scope','scope-item-type') else 'write'
            value = self.envelope(kind)
            if name == 'missing-intent': del value['intent']
            elif name == 'missing-operation-id': del value['intent']['operation_id']
            elif name == 'extra-envelope': value['unexpected'] = 1
            elif name == 'session-type': value['session'] = 1
            elif name == 'boolean-epoch': value['presented_epoch'] = True
            elif name == 'overflow-epoch': value['presented_epoch'] = 1 << 64
            elif name == 'boolean-task-revision': value['intent']['task_revision'] = True
            elif name == 'unordered-add': value['intent']['mutation']['add'] = ['red','blue']
            elif name == 'duplicate-add': value['intent']['mutation']['add'] = ['red','red']
            elif name == 'unordered-scope': value['intent']['scope'] = ['write:catalog','read:receipts']
            elif name == 'scope-item-type': value['intent']['scope'] = ['write:catalog',1]
            elif name == 'missing-mutation': del value['intent']['mutation']
            else: self.fail(name)
            cases[name] = (kind,self.wire(value))
        self.assertEqual(set(cases),set(self.plan['pre_dispatch_invalid']))
        for name,(kind,raw) in cases.items():
            with self.subTest(name=name): self.refusal(kind,raw)

    def test_transport_and_exact_bounds(self):
        cases = {'duplicate-key':b'{"session":"a","session":"b"}',
                 'non-bytes':'{}','byte-overflow':b' '*65537,
                 'depth-overflow':b'['*65+b'0'+b']'*65}
        self.assertEqual(set(cases),set(self.plan['transport_refusals']))
        for name,raw in cases.items():
            with self.subTest(name=name): self.refusal('write',raw,'transport-refusal',name)
        self.refusal('write',b'['*64+b'0'+b']'*64)
        raw = self.wire(self.envelope()); raw += b' '*(65536-len(raw))
        receiver = self.receiver(); result = deliver(receiver,'write',raw)
        self.assertEqual(result['response']['value'],self.fixture(self.plan['write_receipt']))
        self.assertEqual(receiver.calls,1)

    def test_valid_receipts_retry_and_semantic_order(self):
        for kind in ('write','transfer'):
            with self.subTest(kind=kind):
                receiver=self.receiver();raw=self.wire(self.envelope(kind))
                result=deliver(receiver,kind,raw)
                self.assertEqual(result['response']['value'],self.fixture(self.plan[kind+'_receipt']))
                self.assertEqual(receiver.calls,1)
                self.assertIs(result['committed'],True)
                if kind=='write':
                    committed=receiver.snapshot();retry=deliver(receiver,kind,raw)
                    self.assertEqual(retry['response'],result['response'])
                    self.assertEqual(receiver.snapshot(),committed)
                    self.assertEqual(retry['operation_receipt_count'],1)
                    self.assertIs(retry['state_changed'],False)
        for epoch in (4,3):
            receiver=self.receiver();value=self.envelope();value['presented_epoch']=epoch
            value['intent']['mutation']['add']=['BAD']
            result=deliver(receiver,'write',self.wire(value));self.assertEqual(receiver.calls,1)
            if epoch==4:
                self.assertEqual(result['response']['outcome'],{'kind':'refusal-committed','reason':'contract-refusal','observed_record_revision':10,'detail':'invalid-tag'})
                self.assertEqual(result['operation_receipt_count'],1)
            else:
                self.assertEqual(result['response'],{'kind':'current-refusal','reason':'epoch-mismatch'})
                self.assertEqual(result['operation_receipt_count'],0)
            self.assertEqual(result['record'],{'revision':10,'tags':['blue','manual']})

if __name__ == '__main__': unittest.main()
