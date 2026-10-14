"""Pure P0 model; trusted synthetic fixtures only; candidate bytes never run."""
from copy import deepcopy
from hashlib import sha256

BINDINGS = ('candidate_bytes_sha256', 'code_revision', 'base_snapshot_revision',
            'behavior_revision', 'contract_revision')

class Admission:
    def __init__(self, state, sessions):
        self._state = deepcopy(state)
        self._sessions = deepcopy(sessions)

    def snapshot(self):
        return deepcopy(self._state)

    def fixture_revoke(self, principal, grant):
        for row in self._sessions.values():
            if row['principal'] == principal:
                row['grants'] = [g for g in row['grants'] if g != grant]

    def fixture_contract(self, revision):
        self._state['contract_revision'] = revision

    def command(self, kind, session, candidate):
        if kind not in ('retain_candidate', 'attempt_admission'):
            raise ValueError('UNSUPPORTED_COMMAND')
        # Inputs are frozen, well-shaped synthetic records, not a wire parser.
        c = deepcopy(candidate)
        s = self._state
        cid = c['candidate_id']
        technical = False
        admitted = False

        def current(record):
            return all(record[k] == s[('selected_' + k) if k in BINDINGS[:2] else k]
                       for k in BINDINGS)

        def finish(response):
            retained = s['retained_candidates'].get(cid)
            historical = [r for r in s['admission_records'] if r['candidate_id'] == cid]
            return deepcopy({'response': response, 'retained': retained is not None,
                'retained_candidate_count': len(s['retained_candidates']),
                'retained_candidate_sha256': retained['candidate_bytes_sha256'] if retained else None,
                'admitted': admitted, 'executed': False,
                'technical_checks_performed': technical,
                'admission_record_count': len(s['admission_records']),
                'historical_admission_preserved': bool(historical),
                'current_admission_applicable': any(current(r) for r in historical)})

        def refuse(reason, category=None):
            category = category or ('retention-refusal' if kind == 'retain_candidate' else 'admission-refusal')
            return finish({'kind': category, 'reason': reason})

        auth = self._sessions.get(session)
        if not auth or not auth['authenticated']:
            return refuse('authentication-required', 'current-refusal')
        grant = 'candidate:store' if kind == 'retain_candidate' else 'candidate:admit'
        if grant not in auth['grants']:
            return refuse('retention-scope-required' if kind == 'retain_candidate' else 'admission-scope-required', 'current-refusal')
        technical = True
        if kind == 'retain_candidate':
            if sha256(c['candidate_payload_utf8'].encode('utf-8')).hexdigest() != c['candidate_bytes_sha256']:
                return refuse('candidate-digest-mismatch')
            if len(c['evidence_ids']) > 1:
                return refuse('candidate-evidence-cardinality')
            retained = s['retained_candidates'].get(cid)
            if retained is not None and retained != c:
                return refuse('candidate-id-conflict')
            if retained is None:
                s['retained_candidates'][cid] = deepcopy(c)
            return finish({'kind': 'retained', 'candidate_id': cid,
                           'candidate_bytes_sha256': c['candidate_bytes_sha256']})
        retained = s['retained_candidates'].get(cid)
        if retained is None:
            return refuse('candidate-not-retained')
        if retained != c:
            return refuse('retained-candidate-mismatch')
        if any(c[k] != s['selected_' + k] for k in BINDINGS[:2]):
            return refuse('code-stale')
        for key, reason in zip(BINDINGS[2:], ('base-stale', 'behavior-stale', 'contract-stale')):
            if c[key] != s[key]:
                return refuse(reason)
        ids = c['evidence_ids']
        e = s['trusted_evidence'].get(ids[0]) if len(ids) == 1 else None
        if e is None or e.get('result') != 'pass':
            return refuse('mandatory-evidence-unknown')
        if (any(e.get(k) != c[k] for k in BINDINGS)
                or any(e.get(k) != v for k, v in s['mandatory_requirement'].items())
                or e.get('evidence_id') != ids[0]):
            return refuse('evidence-not-applicable')
        record = {'admission_record_id': 'admission-' + cid, 'candidate_id': cid,
                  **{k: c[k] for k in BINDINGS},
                  'requirement_assertion': s['mandatory_requirement']['assertion'],
                  'evidence_id': ids[0]}
        if record not in s['admission_records']:
            s['admission_records'].append(deepcopy(record))
        admitted = True
        return finish({'kind': 'admitted', 'value': record})
