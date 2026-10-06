"""Ordinary-library competitor: pure finite evidence compatibility, no authority."""
DIMENSIONS = ('domain', 'subject', 'revision', 'method', 'binding', 'scope')
ENUMS = {'domain': {'artifact', 'request'}, 'subject': {'A', 'B'},
         'method': {'bytes', 'static', 'runtime'},
         'binding': {'fixture', 'consumer', 'detached'},
         'scope': {'partial', 'complete'}}

def common(x):
    return (type(x) is dict and
            all(type(x.get(k)) is str and x[k] in values for k, values in ENUMS.items()) and
            type(x.get('revision')) is int and 0 <= x['revision'] <= 2)

def evaluate(requirement, receipts):
    def result(decision, reason):
        return {'decision': decision, 'reason': reason}
    if not (common(requirement) and set(requirement) == set(DIMENSIONS) and
            requirement['scope'] == 'complete'):
        return result('invalid', 'requirement')
    if type(receipts) is not list or len(receipts) > 16:
        return result('invalid', 'receipts')
    for r in receipts:
        if not (common(r) and set(r) == set(DIMENSIONS) | {'outcome', 'selected'} and
                type(r.get('outcome')) is str and r['outcome'] in {'pass', 'unknown', 'refuted', 'withdrawn'} and
                type(r.get('selected')) is int and 0 <= r['selected'] <= 2 and
                (r['method'] == 'runtime' or r['selected'] == 0)):
            return result('invalid', 'receipts')
    matches = [r for r in receipts if all(r[k] == requirement[k] for k in DIMENSIONS)]
    passed = any(r['outcome'] == 'pass' and (r['method'] != 'runtime' or r['selected'] > 0) for r in matches)
    conflict = any(r['outcome'] in {'refuted', 'withdrawn'} for r in matches)
    if passed and conflict:
        return result('pending', 'conflicting-evidence')
    if passed:
        return result('accepted', 'matching-pass')
    return result('pending', 'no-applicable-pass')
