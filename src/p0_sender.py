"""Pure sender journal model; committed memory is an assumed durable image.

No I/O, network, ID allocation, authentication or real crash durability.
Caller effect handles are trusted identity inputs, not semantic deduplication.
"""
from copy import deepcopy
from .p0_receiver import ident, uint, valid_intent

class Sender:
    def __init__(self):
        self._rows = {}
        self._ids = {}
        self._crashed = False

    def snapshot(self):
        return deepcopy({'rows': self._rows, 'ids': self._ids})

    def _live(self):
        if self._crashed:
            raise ValueError('SENDER_REQUIRES_RECOVERY')

    def save(self, kind, handle, intent):
        self._live()
        if kind not in ('write', 'transfer') or not ident(handle):
            raise ValueError('SENDER_INVALID_KEY')
        if not valid_intent(intent, kind == 'transfer'):
            raise ValueError('SENDER_INVALID_INTENT')
        key = (kind, intent['task_id'], handle)
        receipt_id = intent['transfer_id' if kind == 'transfer' else 'operation_id']
        id_key = (kind, intent['task_id'], receipt_id)
        if key in self._rows:
            if self._rows[key] != intent:
                raise ValueError('SENDER_HANDLE_CONFLICT')
            return
        if id_key in self._ids:
            raise ValueError('SENDER_ID_CONFLICT')
        # One synthetic commit point; no partial-storage claim.
        rows, ids = deepcopy(self._rows), deepcopy(self._ids)
        rows[key], ids[id_key] = deepcopy(intent), handle
        self._rows, self._ids = rows, ids

    def prepare(self, kind, task_id, handle, session, epoch=None):
        self._live()
        if (kind not in ('write', 'transfer') or not ident(task_id)
                or not ident(handle) or type(session) is not str
                or (kind == 'write' and not uint(epoch))
                or (kind == 'transfer' and epoch is not None)):
            raise ValueError('SENDER_INVALID_CONTEXT')
        key = (kind, task_id, handle)
        if key not in self._rows:
            raise ValueError('SENDER_UNSAVED')
        request = {'session': session, 'intent': deepcopy(self._rows[key])}
        if kind == 'write':
            request['presented_epoch'] = epoch
        return request

    def crash(self):
        self._live()
        self._crashed = True

    def recover(self):
        if not self._crashed:
            raise ValueError('SENDER_NOT_CRASHED')
        # Committed image survives this model cut, including both indexes.
        self._rows, self._ids = deepcopy(self._rows), deepcopy(self._ids)
        self._crashed = False
