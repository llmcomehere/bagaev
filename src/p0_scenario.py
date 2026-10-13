"""Synthetic loss and commit-cut model. Never injects real process/storage faults."""
from copy import deepcopy
from .p0_receiver import Receiver

class Scenario:
    def __init__(self, initial, sessions):
        self.receiver = Receiver(initial, sessions)
        self.responses = {}
        self.delayed = {}
        self.knowledge = {}
        self.crashed = False
        self.committed_state = None
        self.committed_sessions = None

    def observe(self, response=None):
        state = self.receiver.snapshot()
        return {'response': deepcopy(response), 'record_revision': state['record']['revision'],
                'record': state['record'], 'authority_epoch': state['authority']['epoch'],
                'assignee': state['authority']['assignee'],
                'operation_receipt_count': len(state['operation_receipts']),
                'transfer_receipt_count': len(state['transfer_receipts'])}

    def delivery(self, step):
        event = step['event']
        if event in ('deliver_write', 'deliver_transfer'):
            key = step['intent']['operation_id' if event == 'deliver_write' else 'transfer_id']
            result = self.receiver.command(event[len('deliver_'):], step['session'],
                                           step['intent'], step.get('presented_epoch'))
        elif event in ('query_operation', 'query_transfer'):
            key = step['operation_id' if event == 'query_operation' else 'transfer_id']
            result = self.receiver.command(event, step['session'], task_id=step['task_id'], receipt_id=key)
        else:
            raise ValueError('SCENARIO_DELIVERY')
        response = result['response']
        if response['kind'] == 'receipt':
            value = response['value']
            self.knowledge[key] = value['outcome']['kind'] if 'outcome' in value else 'transfer-committed'
        # Absent-at-query or a current refusal cannot settle an earlier unknown effect.
        result['observer'] = self.knowledge.get(key, 'unknown-outcome')
        result['new_operation_id_permitted_for_blind_retry'] = False
        self.responses[key] = deepcopy(response)
        return result

    def event(self, step):
        event = step['event']
        if self.crashed and event != 'recover':
            raise ValueError('SCENARIO_REQUIRES_RECOVERY')
        if event.startswith('deliver_') and event not in ('deliver_delayed_response', 'deliver_cancel'):
            return self.delivery(step)
        if event.startswith('query_'):
            return self.delivery(step)
        if event == 'lose_response':
            key = step['for']
            if key not in self.responses:
                raise ValueError('SCENARIO_MISSING_RESPONSE')
            del self.responses[key]
            self.knowledge[key] = 'unknown-outcome'
            return {'observer': self.knowledge[key]}
        if event == 'delay_response':
            key = step['for']
            if key not in self.responses or key in self.delayed:
                raise ValueError('SCENARIO_DELAY')
            self.delayed[key] = self.responses.pop(key)
            self.knowledge[key] = 'unknown-outcome'
            return {'observer': self.knowledge[key]}
        if event == 'deliver_delayed_response':
            key = step['for']
            if key not in self.delayed:
                raise ValueError('SCENARIO_MISSING_DELAY')
            response = self.delayed.pop(key)
            # Delivery alone never writes receiver state or replays the command.
            self.responses[key] = deepcopy(response)
            if response['kind'] == 'receipt':
                value = response['value']
                self.knowledge[key] = value['outcome']['kind'] if 'outcome' in value else 'transfer-committed'
            result = self.observe(response)
            result['observer'] = self.knowledge.get(key, 'unknown-outcome')
            return result
        if event == 'timeout_before_delivery':
            intent = step['request']
            key = intent.get('operation_id', intent.get('transfer_id'))
            if type(key) is not str:
                raise ValueError('SCENARIO_INTENT')
            self.knowledge[key] = 'unknown-outcome'
            return {'observer': self.knowledge[key]}
        if event == 'deliver_cancel':
            key = step['operation_id']
            return {'response': {'kind': 'current-refusal', 'reason': 'unsupported-action'},
                    'observer': self.knowledge.get(key, 'unknown-outcome'),
                    'guaranteed_stop': False, 'state_changed': False}
        if event in ('crash_before_commit', 'crash_after_commit_before_response'):
            before = self.receiver.snapshot()
            sessions = deepcopy(self.receiver._sessions)
            speculative = Scenario(before, sessions)
            request = {k: deepcopy(v) for k, v in step.items() if k not in ('expect', 'operation', 'event')}
            request['event'] = step['operation']
            result = speculative.delivery(request)
            if not result['committed']:
                raise ValueError('SCENARIO_NO_COMMIT_CUT')
            self.committed_state = (before if event == 'crash_before_commit'
                                    else speculative.receiver.snapshot())
            self.committed_sessions = sessions
            self.crashed = True
            key = step['intent'].get('operation_id', step['intent'].get('transfer_id'))
            self.knowledge[key] = 'unknown-outcome'
            return {'observer': 'unknown-outcome'}
        if event == 'recover':
            if not self.crashed:
                raise ValueError('SCENARIO_NOT_CRASHED')
            self.receiver = Receiver(self.committed_state, self.committed_sessions)
            self.crashed = False
            return self.observe()
        if event == 'withhold_handler_response':
            probe = Scenario(self.receiver.snapshot(), self.receiver._sessions)
            result = probe.delivery(step['after_valid_delivery'])
            if not result['receipt_lookup_performed']:
                raise ValueError('SCENARIO_INVALID_HANDLER_INPUT')
            # Explicit nonconforming fixture action after a valid handled request.
            return {'verdict': 'system-obligation-failure', 'network_assumption_failure': False,
                    'conforming_implementation': False}
        raise ValueError('SCENARIO_EVENT')
