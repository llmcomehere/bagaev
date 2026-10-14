"""Finite serial order enumeration and explicit stale-receiver counterexample."""
from copy import deepcopy
from itertools import permutations
from .p0_receiver import Receiver

def transfer_orders(initial, sessions, requests):
    if len(requests) != 2:
        raise ValueError('TWO_REQUEST_SCOPE')
    observed, final_states = [], []
    for order in permutations(requests):
        model = Receiver(initial, sessions)
        rows = []
        for request in order:
            result = model.command('transfer',request['session'],request['intent'])
            response = result['response']
            row = {'intent':request['fixture_name'],'kind':response['kind']}
            if 'reason' in response:
                row['reason'] = response['reason']
            rows.append(row)
        observed.append(rows)
        final_states.append(model.snapshot())
    epochs = {s['authority']['epoch'] for s in final_states}
    counts = {len(s['transfer_receipts']) for s in final_states}
    if len(epochs) != 1 or len(counts) != 1:
        raise ValueError('ORDER_FINAL_AGREEMENT')
    epoch, count = epochs.pop(), counts.pop()
    return {'serial_observations': [
        {'allowed_serial_results': trace, 'authority_epoch': epoch,
         'transfer_receipt_count': count} for trace in observed]}

def stale_receiver(initial,sessions,coordinator_epoch,receiver_epoch,intent):
    # The explicitly broken integration never informs the receiver of transfer.
    state = deepcopy(initial)
    if coordinator_epoch <= receiver_epoch or state['authority']['epoch'] != receiver_epoch:
        raise ValueError('STALE_COUNTEREXAMPLE_SCOPE')
    principal = state['authority']['assignee']
    matching = [name for name,s in sessions.items() if s['principal'] == principal and s['authenticated']]
    if len(matching) != 1:
        raise ValueError('COUNTEREXAMPLE_SESSION')
    model = Receiver(state,sessions)
    response = model.command('write',matching[0],intent,receiver_epoch)
    effect = response['committed'] and model.snapshot()['record'] != state['record']
    return {'late_write_possible':effect,
            'verdict':'guarantee-failure' if effect else 'counterexample-not-established',
            'conforming_implementation':False,
            'receiver_observation':response}
