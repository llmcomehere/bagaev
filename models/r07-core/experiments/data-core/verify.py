#!/usr/bin/env python3
"""Finite DATA-0.1 verifier with independent values, traces and work interpreter.

No finite report is a universal law proof or full-language conformance. The
oracle does not import the engine. Invalid inputs have authored diagnostics,
not acceptance through a second copy of the implementation typechecker.
"""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROFILE = 'data-core/r07-v1'
CODEC = 'data-wire/r07-v1'
BUDGET = 65536
OPS = {'record','variant','sequence','map_build','field','equal','compare','length',
       'seq_get','seq_append','map_get','utf8_encode','utf8_decode','encode','decode'}
RULES = {'JOB_START','JOB_FINISH','RECORD_FIELD','VARIANT_WRAP','SEQUENCE_ITEM',
         'FIELD_SELECT','LENGTH_ITEM','SEQ_GET','SEQUENCE_APPEND','COMPARE_NODE',
         'COMPARE_UNIT','COMPARE_END','COMPARE_NEXT','MAP_STAGE','MAP_PROBE',
         'MAP_DECIDE','MAP_COPY','MAP_ADD','MAP_COMMIT','MAP_LOOKUP',
         'MAP_LOOKUP_DECIDE','MAP_LOOKUP_END','UTF8_SCALAR','UTF8_WRITE',
         'UTF8_READ','UTF8_END','ENCODE_WRITE','ENCODE_NODE','ENCODE_NEXT',
         'ENCODE_SCAN','ENCODE_SCALAR','DECODE_READ','DECODE_NODE','DECODE_NEXT',
         'DECODE_SCALAR','DECODE_LENGTH','DECODE_TAG','DECODE_ASSEMBLE',
         'DECODE_MAP_ORDER','DECODE_END'}
SOURCES = ['experiments/data-core/engine.py','experiments/data-core/API.md',
           'experiments/data-core/README.md','experiments/data-core/oracle.py',
           'experiments/data-core/verify.py','experiments/data-core/authorship_bridge.py',
           'fixtures/data-core.json']


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(x):
    return sha256(canon(x).encode('utf-8')).hexdigest()


def hashes():
    return {path: sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCES}


def raw_value(t, d):
    return {'type': deepcopy(t), 'data': deepcopy(d)}


def result_type(t):
    return {'tag': 'result', 'ok': deepcopy(t), 'err': 'DataError'}


def job(source, op, schemas):
    return {'source_id': source, 'revision': '1', 'profile_revision': PROFILE,
            'schemas': deepcopy(schemas), 'operation': deepcopy(op)}


def header(schemas, typ):
    registry = digest({'profile_revision': PROFILE, 'codec_revision': CODEC, 'schemas': schemas})
    type_stamp = digest({'profile_revision': PROFILE, 'codec_revision': CODEC, 'type': typ})
    return [66, 68, 48, 55, 1] + list(bytes.fromhex(registry + type_stamp))


def difference(a, b, path=()):
    if type(a) is not type(b):
        return {'path': list(path), 'actual': repr(a)[:500], 'expected': repr(b)[:500]}
    if isinstance(a, dict):
        if set(a) != set(b): return {'path': list(path), 'actual_keys': sorted(a), 'expected_keys': sorted(b)}
        for key in a:
            d = difference(a[key], b[key], path + (key,))
            if d: return d
    elif isinstance(a, list):
        if len(a) != len(b): return {'path': list(path), 'actual_length': len(a), 'expected_length': len(b)}
        for i, (x, y) in enumerate(zip(a, b)):
            d = difference(x, y, path + (i,))
            if d: return d
    elif a != b:
        return {'path': list(path), 'actual': repr(a)[:500], 'expected': repr(b)[:500]}
    return None


def eq(a, b, label):
    d = difference(a, b)
    if d: raise AssertionError(label + ': ' + json.dumps(d, ensure_ascii=True))


def trace(rows):
    return [{'step_index': i + 1, 'rule': rule, 'path': path} for i, (rule, path) in enumerate(rows)]


def expected_receipt(raw, value, rows, budget=BUDGET):
    return {'profile_revision': PROFILE, 'codec_revision': CODEC,
            'content_digest': digest({'profile_revision': PROFILE, 'codec_revision': CODEC, 'job': raw}),
            'registry_digest': digest({'profile_revision': PROFILE, 'codec_revision': CODEC, 'schemas': raw['schemas']}),
            'termination': 'RETURNED', 'code': 'RETURNED', 'value': deepcopy(value),
            'steps': len(rows), 'remaining': budget - len(rows), 'trace': trace(rows), 'cancel_request_id': None}


def receipt_view(result, include_trace=False):
    view = {k: deepcopy(v) for k, v in result.items() if k != 'trace'}
    # Large successful wire values are bound exactly by full_observation_sha256.
    if len(canon(view.get('value'))) > 1600:
        view['value'] = {'recorded_separately_as_sha256': digest(result['value'])}
    view['full_observation_sha256'] = digest(result)
    view['trace_sha256'] = digest(result['trace'])
    if include_trace: view['trace'] = result['trace']
    return view


class Verifier:
    def __init__(self, fixture, engine, oracle, bridge):
        self.fixture, self.engine, self.oracle, self.bridge = fixture, engine, oracle, bridge
        self.sections = {}
        self.jobs = {}
        self.operations = set()
        self.rules = set()
        self.mismatches = 0
        self.named = 0
        self.passed = 0
        self.matrix_cases = 0

    def check(self, section, ident, fn):
        self.named += 1
        try:
            detail = fn()
            row = {'id': ident, 'passed': True, **(detail or {})}
            self.passed += 1
        except Exception as error:
            row = {'id': ident, 'passed': False, 'error_type': type(error).__name__,
                   'error': str(error), 'location': traceback.format_exc(limit=3)}
        self.sections.setdefault(section, []).append(row)
        return row

    def engine_run(self, raw, budget=BUDGET, *, cancel_at=None, cancel_request_id='cancel', engine=None):
        e = self.engine if engine is None else engine
        result = e.run(e.decode_job(deepcopy(raw)), budget, cancel_at=cancel_at,
                       cancel_request_id=cancel_request_id)
        return e.execution_json(result)

    def pair(self, raw, budget=BUDGET, *, cancel_at=None, cancel_request_id='cancel'):
        got = self.engine_run(raw, budget, cancel_at=cancel_at, cancel_request_id=cancel_request_id)
        wanted = self.oracle.run(deepcopy(raw), budget, cancel_at=cancel_at,
                                 cancel_request_id=cancel_request_id)
        if difference(got, wanted): self.mismatches += 1
        eq(got, wanted, 'whole engine/oracle observation')
        self.operations.add(raw['operation']['op'])
        self.rules.update(row['rule'] for row in got['trace'])
        return got

    def authored(self):
        for case in self.fixture['programs']:
            raw = case['job']; self.jobs[case['id']] = raw
            def one(case=case, raw=raw):
                result = self.pair(raw)
                expected = expected_receipt(raw, case['expected']['value'], case['expected']['trace'])
                eq(result, expected, 'authored complete receipt')
                return {'description': case['description'], 'observation': receipt_view(result, True),
                        'authored_value_and_trace': True}
            self.check('authored_jobs', case['id'], one)

    def unicode(self):
        scalar_widths = {'U00':[1], 'U01':[3], 'U02':[3], 'U03':[4], 'U04':[4],
                         'U05':[2], 'U06':[1,2], 'U07':[1,4,2], 'U08':[]}
        for vec in self.fixture['unicode_vectors']:
            enc_rows = [['JOB_START', []]]; offset = 0
            for i, width in enumerate(scalar_widths[vec['id']]):
                enc_rows.append(['UTF8_SCALAR', ['value', i]])
                enc_rows += [['UTF8_WRITE', ['bytes', n]] for n in range(offset, offset + width)]
                offset += width
            enc_rows += [['JOB_FINISH', []]]
            dec_rows = [['JOB_START', []]] + [['UTF8_READ', ['bytes', i]] for i in range(vec['byte_length'])] + [['UTF8_END', ['bytes']], ['JOB_FINISH', []]]
            cases = [
                ('utf8_encode', {'op':'utf8_encode','value':raw_value('String',vec['text'])}, raw_value('Bytes',vec['utf8']), enc_rows),
                ('utf8_decode', {'op':'utf8_decode','value':raw_value('Bytes',vec['utf8'])}, raw_value(result_type('String'),{'tag':'Ok','value':vec['text']}), dec_rows),
                ('scalar_length', {'op':'length','value':raw_value('String',vec['text'])}, raw_value('Int64',vec['scalar_length']), [['JOB_START',[]]] + [['LENGTH_ITEM',['value',i]] for i in range(vec['scalar_length'])] + [['JOB_FINISH',[]]]),
                ('byte_length', {'op':'length','value':raw_value('Bytes',vec['utf8'])}, raw_value('Int64',vec['byte_length']), [['JOB_START',[]]] + [['LENGTH_ITEM',['value',i]] for i in range(vec['byte_length'])] + [['JOB_FINISH',[]]])]
            for suffix, op, want, rows in cases:
                ident = vec['id'] + ':' + suffix
                raw = job(ident, op, self.fixture['schemas']); self.jobs[ident] = raw
                def one(raw=raw, want=want, rows=rows):
                    result = self.pair(raw)
                    eq(result, expected_receipt(raw, want, rows), 'authored UTF8/scalar receipt')
                    return {'observation': receipt_view(result), 'authored_value_and_trace': True}
                self.check('unicode', ident, one)
        for vec in self.fixture['invalid_utf8_vectors']:
            ident = vec['id']; error = vec['expected_error']
            raw = job(ident, {'op':'utf8_decode','value':raw_value('Bytes',vec['bytes'])}, self.fixture['schemas'])
            count = len(vec['bytes']) if error['code'] == 'Utf8Truncated' else error['first'] + 1
            rows = [['JOB_START', []]] + [['UTF8_READ', ['bytes', i]] for i in range(count)]
            if error['code'] == 'Utf8Truncated': rows += [['UTF8_END', ['bytes']]]
            def one(raw=raw, rows=rows, error=error):
                result = self.pair(raw)
                want = raw_value(result_type('String'), {'tag':'Err','value':error})
                eq(result, expected_receipt(raw, want, rows), 'authored invalid UTF8 receipt')
                return {'observation': receipt_view(result), 'authored_error_and_trace': True}
            self.check('unicode', ident, one)

    def wire(self):
        for vec in self.fixture['wire_body_vectors']:
            wire = header(self.fixture['schemas'], vec['type']) + vec['body']
            enc = job(vec['id'] + ':encode', {'op':'encode','value':raw_value(vec['type'],vec['data'])},self.fixture['schemas'])
            dec = job(vec['id'] + ':decode', {'op':'decode','type':vec['type'],'bytes':raw_value('Bytes',wire)},self.fixture['schemas'])
            self.jobs[vec['id'] + ':encode'] = enc; self.jobs[vec['id'] + ':decode'] = dec
            def one(vec=vec, wire=wire, enc=enc, dec=dec):
                encoded = self.pair(enc); decoded = self.pair(dec)
                eq(encoded['value'], raw_value('Bytes',wire), 'independently authored wire payload/header')
                eq(decoded['value'], raw_value(result_type(vec['type']),{'tag':'Ok','value':vec['data']}), 'authored decoded value')
                if encoded['termination'] != 'RETURNED' or decoded['termination'] != 'RETURNED': raise AssertionError('roundtrip did not return')
                return {'type':vec['type'],'wire_sha256':digest(wire),'wire_bytes':len(wire),
                        'encode':receipt_view(encoded),'decode':receipt_view(decoded),
                        'authored_payload_octets':True,'whole_observations_equal':True}
            self.check('wire_roundtrips',vec['id'],one)
        fault_rules = {'InvalidEncoding':'DECODE_SCALAR','TrailingBytes':'DECODE_END','UnknownVariant':'DECODE_TAG',
                       'Utf8Truncated':'DECODE_SCALAR','UnexpectedEnd':'DECODE_READ','Utf8Surrogate':'DECODE_READ',
                       'NonCanonicalMap':'DECODE_MAP_ORDER','ContextMismatch':'DECODE_READ'}
        for vec in self.fixture['codec_cases']:
            wire = header(self.fixture['schemas'],vec['type']) + vec['body']
            mutation = vec.get('wire_mutation')
            if mutation:
                if mutation['kind'] == 'set': wire[mutation['offset']] = mutation['value']
                elif mutation['kind'] == 'truncate': wire = wire[:mutation['length']]
            raw = job(vec['id'] + ':decode', {'op':'decode','type':vec['type'],'bytes':raw_value('Bytes',wire)},self.fixture['schemas'])
            self.jobs[vec['id'] + ':decode'] = raw
            def one(vec=vec, raw=raw):
                result = self.pair(raw)
                eq(result['value'],raw_value(result_type(vec['type']),{'tag':'Err','value':vec['error']}),'authored codec error')
                eq(result['trace'][-1]['rule'],fault_rules[vec['error']['code']],'faulting charged rule')
                if any(row['rule']=='JOB_FINISH' for row in result['trace']): raise AssertionError('fault incorrectly charged FINISH')
                return {'observation':receipt_view(result),'authored_error':vec['error']}
            self.check('codec_errors',vec['id'],one)

    def diagnostics(self):
        for case in self.fixture['negative_jobs']:
            def one(case=case):
                try: self.engine.prepare(self.engine.decode_job(deepcopy(case['job'])))
                except self.engine.DataCoreError as error:
                    actual = {'code':error.code,'kind':error.kind}
                    eq(actual,case['expected'],'individually authored prelaunch diagnostic')
                    return {'description':case['description'],'expected':case['expected'],'actual':actual,'path':list(error.path)}
                raise AssertionError('invalid job accepted')
            self.check('diagnostics',case['id'],one)
        for ident,kwargs,code in [('D01',{'budget':True},'INVALID_BUDGET'),('D02',{'budget':-1},'INVALID_BUDGET'),('D03',{'budget':262145},'INVALID_BUDGET'),('D04',{'budget':10,'cancel_at':True},'INVALID_CANCELLATION')]:
            def one(kwargs=kwargs,code=code):
                try: self.engine.run(self.engine.decode_job(deepcopy(self.jobs['J08'])),**kwargs)
                except self.engine.DataCoreError as error:
                    eq(error.code,code,'authored control diagnostic')
                    return {'expected':code,'actual':error.code,'kind':error.kind}
                raise AssertionError('invalid budget/cancellation accepted')
            self.check('diagnostics',ident,one)

    def predicates(self):
        reference = self.oracle.Registry(self.fixture['schemas'])
        for case in self.fixture['predicate_cases']:
            def one(case=case):
                actual = {p:self.engine.predicate(self.fixture['schemas'],case['type'],p) for p in ('Eq','Key','Persistable')}
                wanted = {p:reference.predicate(case['type'],p) for p in ('Eq','Key','Persistable')}
                eq(actual,case['expected'],'authored structural predicate')
                eq(actual,wanted,'independent structural predicate')
                return {'type':case['type'],'expected':case['expected'],'actual':actual}
            self.check('predicates',case['id'],one)

    def boundaries(self):
        for case in self.fixture['boundary_cases']:
            if case['kind'] == 'decode_length':
                wire = header(self.fixture['schemas'],case['type']) + case['body']
                op = {'op':'decode','type':case['type'],'bytes':raw_value('Bytes',wire)}
            elif case['kind'] == 'append_limit':
                op = {'op':'seq_append','sequence':raw_value({'tag':'seq','item':'Unit'},[None]*256),'value':raw_value('Unit',None)}
            elif case['kind'] == 'output_limit':
                op = {'op':'encode','value':raw_value('Bytes',[0]*32768)}
            raw = job(case['id'],op,self.fixture['schemas'])
            def one(case=case,raw=raw):
                result = self.pair(raw)
                eq((result['termination'],result['code'],result['steps'],result['value']),('IMPLEMENTATION_STOP',case['code'],case['steps'],None),'authored physical stop')
                # At the same boundary, cancellation and budget are observed before the refusing next unit.
                cancelled = self.pair(raw,case['steps'],cancel_at=case['steps'])
                eq((cancelled['code'],cancelled['steps']),('CANCELLED',case['steps']),'cancel wins physical/budget tie')
                stopped = self.pair(raw,case['steps'])
                eq((stopped['code'],stopped['steps']),('BUDGET_EXCEEDED',case['steps']),'budget precedes next physical refusal')
                return {'physical':receipt_view(result),'cancel_at_boundary':receipt_view(cancelled),
                        'budget_at_boundary':receipt_view(stopped),'whole_observations_equal':True,
                        'scope':'selected explicit physical boundaries, not all allocation policies'}
            self.check('boundaries',case['id'],one)
        def node_headroom():
            typ = {'tag':'seq','item':{'tag':'seq','item':'Unit'}}
            payload = [[None]*256 for _ in range(15)] + [[None]*238]
            raw = job('headroom-nodes',{'op':'encode','value':raw_value(typ,payload)},self.fixture['schemas'])
            encoded = self.pair(raw)
            eq(encoded['termination'],'RETURNED','4095 payload nodes accepted')
            decoded = self.pair(job(raw['source_id'],{'op':'decode','type':typ,'bytes':encoded['value']},self.fixture['schemas']))
            eq(decoded['value'],raw_value(result_type(typ),{'tag':'Ok','value':payload}),'4096-node Ok wrapper accepted')
            bad = deepcopy(raw); bad['operation']['value']['data'][-1].append(None)
            try: self.engine.prepare(self.engine.decode_job(bad))
            except self.engine.DataCoreError as error:
                eq((error.code,error.kind),('PROFILE_LIMIT','UnsupportedInputProfile'),'4096 payload nodes leave no Ok wrapper headroom')
                refused = {'code':error.code,'kind':error.kind}
            else: raise AssertionError('encode admitted payload without result wrapper headroom')
            return {'authored_payload_nodes':4095,'authored_decoded_result_nodes':4096,
                    'encode':receipt_view(encoded),'decode':receipt_view(decoded),'one_more_node':refused,
                    'scope':'one accepted/rejected node boundary, not all memory policies'}
        self.check('boundaries','B05',node_headroom)
        def depth_headroom():
            typ,payload = 'Unit',None
            # Depth counts edges: a scalar leaf has depth zero, nodes one.
            for _ in range(31): typ,payload = {'tag':'seq','item':typ},[payload]
            raw = job('headroom-depth',{'op':'encode','value':raw_value(typ,payload)},self.fixture['schemas'])
            encoded = self.pair(raw)
            eq(encoded['termination'],'RETURNED','depth31 payload accepted')
            decoded = self.pair(job(raw['source_id'],{'op':'decode','type':typ,'bytes':encoded['value']},self.fixture['schemas']))
            eq(decoded['value'],raw_value(result_type(typ),{'tag':'Ok','value':payload}),'depth32 result accepted')
            bad = job('headroom-depth-refused',{'op':'encode','value':raw_value({'tag':'seq','item':typ},[payload])},self.fixture['schemas'])
            try: self.engine.prepare(self.engine.decode_job(bad))
            except self.engine.DataCoreError as error:
                eq((error.code,error.kind),('PROFILE_LIMIT','UnsupportedInputProfile'),'depth32 payload lacks result wrapper headroom')
                refused = {'code':error.code,'kind':error.kind}
            else: raise AssertionError('encode admitted depth32 payload without wrapper headroom')
            return {'authored_payload_depth':31,'authored_result_depth':32,
                    'encode':receipt_view(encoded),'decode':receipt_view(decoded),'one_more_depth':refused}
        self.check('boundaries','B06',depth_headroom)
        def envelope_headroom():
            # Authored finite metadata witness: 64 declarations, 4032 Fn fields.
            # Fn appears in unused metadata only; the encoded value is Bytes.
            schemas = [{'id':'E','revision':'r1','kind':'record','type_params':[],
                        'codec':CODEC,'fields':[]}]
            field_type = {'tag':'fn','params':[],
                          'result':{'tag':'nominal','id':'E','revision':'r1','args':[]}}
            for i in range(63):
                schemas.append({'id':'R'+str(i),'revision':'r1','kind':'record','type_params':[],
                                'codec':None,'fields':[{'id':'f'+str(k),'type':deepcopy(field_type)} for k in range(64)]})
            empty = job('envelope',{'op':'decode','type':'Bytes','bytes':raw_value('Bytes',[])},schemas)
            empty['revision'] = 'r1'
            eq(self.oracle.raw_node_count(schemas),40769,'authored registry node count')
            eq(self.oracle.raw_node_count(empty),40779,'authored empty decoder envelope')
            cap = 24757  # 65536 - 40779; strictly below the ordinary wire cap.
            payload = [0] * (cap - 73)  # 69-byte header + four length bytes.
            enc_job = job('envelope',{'op':'encode','value':raw_value('Bytes',payload)},schemas)
            enc_job['revision'] = 'r1'
            encoded = self.pair(enc_job)
            expected_wire = header(schemas,'Bytes') + list(len(payload).to_bytes(4,'big')) + payload
            eq(encoded['value'],raw_value('Bytes',expected_wire),'wire exactly fits decoder envelope headroom')
            dec_job = deepcopy(empty); dec_job['operation']['bytes'] = encoded['value']
            eq(self.oracle.raw_node_count(dec_job),65536,'exact accepted raw decoder node bound')
            decoded = self.pair(dec_job)
            eq(decoded['value'],raw_value(result_type('Bytes'),{'tag':'Ok','value':payload}),'same-envelope roundtrip at raw bound')
            too_large = deepcopy(enc_job); too_large['operation']['value']['data'] = [0] * cap
            eq(self.oracle.raw_node_count(too_large),65535,'refusing encoder input is itself admissible')
            stopped = self.pair(too_large)
            eq((stopped['termination'],stopped['code'],stopped['steps'],stopped['value']),
               ('IMPLEMENTATION_STOP','OUTPUT_LIMIT',24759,None),'dynamic envelope cap refuses next write without charge')
            return {'registry_raw_nodes':40769,'empty_decode_raw_nodes':40779,'wire_cap':cap,
                    'successful_decode_raw_nodes':65536,'refused_encoder_raw_nodes':65535,
                    'encode':receipt_view(encoded),'decode':receipt_view(decoded),'refused_encode':receipt_view(stopped),
                    'same_labels_registry_type':True,'whole_observations_equal':True,
                    'scope':'one finite maximal raw-envelope witness, not a proof for every registry'}
        self.check('boundaries','B07',envelope_headroom)

    def bindings(self):
        def same_labels():
            a = deepcopy(self.jobs['J08']); b = deepcopy(a); b['operation']['value']['data'] = 'different'
            x,y = self.pair(a),self.pair(b)
            if x['content_digest']==y['content_digest'] or x['value']==y['value']: raise AssertionError('labels reused as content identity')
            return {'same_labels':True,'first':receipt_view(x),'second':receipt_view(y)}
        self.check('bindings','K01',same_labels)
        def registry_binding():
            schemas = deepcopy(self.fixture['schemas']); schemas[0]['fields'].reverse()
            old = header(self.fixture['schemas'],'Unit'); new = header(schemas,'Unit')
            offset = next(i for i,(x,y) in enumerate(zip(old,new)) if x!=y)
            raw = job('same-registry-labels',{'op':'decode','type':'Unit','bytes':raw_value('Bytes',old)},schemas)
            result = self.pair(raw)
            eq(result['value'],raw_value(result_type('Unit'),{'tag':'Err','value':{'code':'ContextMismatch','first':offset,'second':-1}}),'whole actual registry binding')
            return {'changed_unrelated_declaration':True,'observation':receipt_view(result)}
        self.check('bindings','K02',registry_binding)
        def type_binding():
            old = header(self.fixture['schemas'],'Unit'); new = header(self.fixture['schemas'],'Bool')
            offset = next(i for i,(x,y) in enumerate(zip(old,new)) if x!=y)
            raw = job('type-envelope',{'op':'decode','type':'Bool','bytes':raw_value('Bytes',old+[0])},self.fixture['schemas'])
            result = self.pair(raw)
            eq(result['value'],raw_value(result_type('Bool'),{'tag':'Err','value':{'code':'ContextMismatch','first':offset,'second':-1}}),'exact wire type binding')
            return {'observation':receipt_view(result)}
        self.check('bindings','K03',type_binding)
        def prepared():
            raw = deepcopy(self.jobs['J08']); original = deepcopy(raw)
            p = self.engine.prepare(self.engine.decode_job(raw)); raw['operation']['value']['data']='changed after prepare'
            forged = replace(p, content_digest='0'*64, operation={'op':'hidden_builtin'})
            expected = self.oracle.run(original,BUDGET)
            got = self.engine.execution_json(self.engine.run(forged,BUDGET))
            eq(got,expected,'Prepared caches are rebuilt from immutable job')
            machine = self.engine.launch(p,0,cancel_at=0)
            machine = self.engine.step(machine)
            before = self.engine.execution_json(self.engine.execution(machine))
            after = self.engine.execution_json(self.engine.execution(self.engine.step(machine)))
            eq(before,after,'terminal step is free and stable')
            return {'deep_freeze_and_forged_cache_recheck':True,'observation':receipt_view(got),'terminal_step_unchanged':True}
        self.check('bindings','K04',prepared)

    def bridges(self):
        for case in self.fixture['bridge_cases']:
            def one(case=case):
                actual = self.bridge.run_bridge(deepcopy(case['people']),deepcopy(case['articles']),self.engine_run)
                wanted = self.bridge.run_bridge(deepcopy(case['people']),deepcopy(case['articles']),self.oracle.run)
                eq(actual,wanted,'full pure pipeline, including every job and complete observation')
                eq(self.bridge.domain_view(actual),case['expected'],'authored bridge domain result')
                for row in actual['jobs']:
                    self.operations.add(row['job']['operation']['op'])
                    self.rules.update(x['rule'] for x in row['observation']['trace'])
                return {'authored_expected':case['expected'],'domain_result':self.bridge.domain_view(actual),
                        'job_count':len(actual['jobs']),'job_roles':[r['role'] for r in actual['jobs']],
                        'full_pipeline_sha256':digest(actual),'independent_pipeline_sha256':digest(wanted),
                        'job_receipts':[{'role':r['role'],'content_digest':r['observation']['content_digest'],
                                         'steps':r['observation']['steps'],'full_observation_sha256':digest(r['observation'])} for r in actual['jobs']],
                        'whole_pipeline_equal':True,'python_coordinator_not_language_program':True}
            self.check('authorship_bridge',case['id'],one)

    def matrix(self):
        selected = {'J04':list(range(14)), 'J15':list(range(10)), 'J19':list(range(21)),
                    'U04:utf8_encode':list(range(9)),
                    'W07:encode':[0,1,2,68,69,70,71,73,74,75,76,77,78,80,88,89,90],
                    'C04:decode':[0,1,68,69,70,71,74,75,76,77,78,79,80]}
        eq(sorted(selected),sorted(self.fixture['bounded_matrix']['case_refs']),'declared matrix roster')
        rows = []
        for ref,boundaries in selected.items():
            raw = self.jobs[ref]
            outcomes = {}; cases = []
            for budget in boundaries:
                for cancel in [None,*boundaries]:
                    got = self.pair(raw,budget,cancel_at=cancel,cancel_request_id='matrix-cancel')
                    self.matrix_cases += 1
                    outcomes[got['code']] = outcomes.get(got['code'],0)+1
                    cases.append({'budget':budget,'cancel_at':cancel,'steps':got['steps'],
                                  'termination':got['termination'],'code':got['code'],
                                  'full_observation_sha256':digest(got),'trace_sha256':digest(got['trace'])})
            rows.append({'job_ref':ref,'budget_values':boundaries,'cancel_values':[None,*boundaries],
                         'cases':len(cases),'outcome_counts':outcomes,'whole_observations_equal':True,
                         'case_results':cases})
        self.sections['bounded_matrix'] = {'job_count':len(rows),'cases':self.matrix_cases,
            'mismatches':0,'rows':rows,'scope':'Cartesian product of exactly listed finite budgets/cancel offsets; no universal result'}

    def mutations(self):
        source = (HERE/'engine.py').read_text()
        changes = [
            ('M01','admit_duplicate_key_as_less','J19',None,
             'if result == 0: raise _DataFailure("DuplicateKey", prefix[i][2], j)',
             'if result == 0: result = -1  # TEST MUTANT: admit equal key'),
            ('M02','silently_normalize_input_strings_to_NFC','J06',None,
             'v = _make(t, "String", raw)',
             'v = _make(t, "String", __import__("unicodedata").normalize("NFC", raw))'),
            ('M03','skip_visible_cancellation_after_startup','U04:utf8_encode',2,
             'if machine.cancel_at is not None and machine.steps >= machine.cancel_at:',
             'if machine.cancel_at is not None and machine.steps >= machine.cancel_at and machine.steps <= 1:'),
        ]
        for ident,defect,ref,cancel,needle,replacement in changes:
            def one(ident=ident,defect=defect,ref=ref,cancel=cancel,needle=needle,replacement=replacement):
                if source.count(needle)!=1: raise AssertionError('mutation must bind exactly one stable source site')
                changed = source.replace(needle,replacement,1)
                name = 'executed_data_mutant_' + ident
                module = ModuleType(name); module.__file__ = str(HERE/'engine.py')
                sys.modules[name] = module
                exec(compile(changed,str(HERE/('mutant_'+ident+'.py')),'exec'),module.__dict__)
                raw = self.jobs[ref]
                correct = self.pair(raw,cancel_at=cancel)
                actual = self.engine_run(raw,cancel_at=cancel,engine=module)
                if actual==correct: raise AssertionError('mutant survived actual execution')
                if ident=='M01':
                    eq(correct['value']['data']['tag'],'Err','baseline duplicate rejection')
                    eq(actual['value']['data']['tag'],'Ok','mutant actually admits duplicates')
                elif ident=='M02':
                    eq((correct['value']['data'],actual['value']['data']),(False,True),'mutant actually changes Unicode equality')
                else:
                    eq((correct['code'],actual['code']),('CANCELLED','RETURNED'),'mutant actually executes past visible cancellation')
                return {'defect':defect,'job_ref':ref,'cancel_at':cancel,'executed':True,'killed':True,
                        'source_site_occurrences':1,'source_replacement':{'before':needle,'after':replacement},
                        'mutated_source_sha256':sha256(changed.encode('utf-8')).hexdigest(),
                        'baseline':receipt_view(correct,True),'mutant':receipt_view(actual,True),
                        'first_difference':difference(actual,correct),
                        'scope':'a concrete mutant execution caught by the independent observation; not mutation-score completeness'}
            self.check('mutants',ident,one)

    def coverage(self):
        def one():
            eq(sorted(self.operations),sorted(OPS),'all fifteen operations exercised')
            eq(sorted(self.rules),sorted(RULES),'published charged rule roster exercised')
            tree = ast.parse((HERE/'oracle.py').read_text())
            imported = []
            for node in ast.walk(tree):
                if isinstance(node,ast.Import): imported.extend(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom): imported.append(node.module or '')
            if any(any(word in name for word in ('engine','laws','core_machine','call_profile')) for name in imported): raise AssertionError('oracle imports tested semantics')
            return {'operations_expected':sorted(OPS),'operations_seen':sorted(self.operations),
                    'charged_rule_ids_expected':sorted(RULES),'charged_rule_ids_seen':sorted(self.rules),'oracle_imports':sorted(imported),
                    'independence':'separate plain values + deferred-action generator; manually authored values/wire/traces; invalid inputs have individual expected codes'}
        self.check('coverage','V01',one)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',default='results/data-core/report.json')
    parser.add_argument('--smoke',action='store_true',help='targeted named comparisons only; writes no evidence report')
    args = parser.parse_args()
    fixture = json.loads((ROOT/'fixtures/data-core.json').read_text())
    engine = load('data_engine_under_test',HERE/'engine.py')
    oracle = load('independent_data_oracle',HERE/'oracle.py')
    bridge = load('data_authorship_bridge',HERE/'authorship_bridge.py')
    started = time.monotonic()
    initial_hashes = None if args.smoke else hashes()
    v = Verifier(fixture,engine,oracle,bridge)
    v.authored(); v.unicode(); v.wire(); v.diagnostics(); v.predicates(); v.bindings(); v.bridges()
    if args.smoke:
        failed = [row for rows in v.sections.values() for row in rows if not row['passed']]
        print(json.dumps({'mode':'targeted_smoke_no_report','checks':v.named,'passed':v.passed,'failures':failed},ensure_ascii=True,indent=2))
        return 0 if not failed else 1
    v.boundaries()
    v.check('matrix_checks','MATRIX',lambda:(v.matrix() or {'cases':v.matrix_cases,'whole_observations_equal':True}))
    v.mutations(); v.coverage()
    stable = hashes()==initial_hashes
    status = 'PASS' if v.named==v.passed and stable and v.mismatches==0 else 'FAIL'
    report = {'schema':'bagaev-data-report/0.1','status':status,'profile_revision':PROFILE,'codec_revision':CODEC,
              'scope':{'bagaev_execution':False,'research_data_execution':True,'research_ast_execution':False,
                       'source_expression_execution':False,'hypothesis_tested':False,'full_v1_conformance':False,
                       'universal_proof':False,'database_execution':False,'durable_authorship_execution':False,
                       'ready_typed_operands':True,'core_call_integration_tested':False,
                       'statement':'Finite typed ready-value jobs and an external Python authorship coordinator; not a source language, durable store, migration, A/B/C or universal proof.',
                       'oracle_limit':'Independent accepted-job work semantics and selected physical guards; invalid input codes authored individually. No complete second typechecker or allocator proof.'},
              'source_sha256':initial_hashes,'source_bytes_stable_during_run':stable,
              'summary':{'named_checks':v.named,'named_passed':v.passed,'named_failed':v.named-v.passed,
                         'whole_observation_mismatches':v.mismatches,'matrix_cases':v.matrix_cases,
                         'operations_exercised':len(v.operations),'charged_rules_exercised':len(v.rules),
                         'authored_jobs':len(fixture['programs']),'wire_vectors':len(fixture['wire_body_vectors']),
                         'bridge_cases':len(fixture['bridge_cases']),
                         'mutants_executed':len(v.sections.get('mutants',[])),
                         'mutants_killed':sum(row['passed'] for row in v.sections.get('mutants',[])),
                         'counts_note':'Named checks are disjoint rows; matrix/boundary/bridge executions may overlap inputs and are not summed as unique programs.'},
              'sections':v.sections,'elapsed_seconds_not_benchmark':round(time.monotonic()-started,6)}
    output = Path(args.output); output = output if output.is_absolute() else ROOT/output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n')
    print(json.dumps({'status':status,'summary':report['summary'],'report':str(output),
                      'report_sha256':sha256(output.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
    return 0 if status=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
