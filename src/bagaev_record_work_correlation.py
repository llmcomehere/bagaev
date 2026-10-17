"""Opt-in root unary/if correlation for conditional logical-work bounds.

No evaluator, source rewriting, execution admission or new argument domain.
The original analyzer remains the authority for unsupported input and budgets.
"""
from bagaev_record_work import analyze as baseline_analyze


def analyze(expression, arguments, functions=None, records=None, lists=None):
    baseline = baseline_analyze(expression, arguments, functions, records, lists)
    result = dict(baseline, schema='bagaev-record-work-correlation/1',
                  refinement='none')
    if baseline['status'] != 'SUPPORTED':
        return result
    result['baseline_upper_work'] = baseline['upper_work']
    if (type(expression) is not list or len(expression) != 2 or
            expression[0] not in ('list.unique', 'list.increasing', 'list.len')):
        return result
    branch = expression[1]
    if type(branch) is not list or len(branch) != 4 or branch[0] != 'if':
        return result
    # Pure analysis identity: U(if c a b) charges the same entered nodes as
    # if c U(a) U(b). Both arms remain checked; c is not duplicated.
    distributed = ['if', branch[1], [expression[0], branch[2]],
                   [expression[0], branch[3]]]
    refined = baseline_analyze(distributed, arguments, functions, records, lists)
    # Distribution adds one statically visited node. Never enlarge the existing
    # budget or lose an otherwise supported conservative answer on that boundary.
    if (refined['status'] != 'SUPPORTED' or
            refined['upper_work'] > baseline['upper_work']):
        return result
    result['upper_work'] = refined['upper_work']
    result['fits_work_budget'] = refined['fits_work_budget']
    result['refinement'] = 'root-unary-if'
    return result
