"""Bounded JSON write/transfer ingress for trusted-fixture P0 receivers.

No I/O, network, candidate execution or production authentication/durability.
Transport admission and frozen P0 malformed-request semantics stay distinct.
"""
import json
from .p0_receiver import fields, uint, valid_intent

BYTE_LIMIT = 65536
DEPTH_LIMIT = 64

class TransportRefusal(ValueError):
    pass

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TransportRefusal('duplicate-key')
        result[key] = value
    return result

def _constant(value):
    raise ValueError('nonfinite-json-constant')

def _transport(raw):
    if type(raw) is not bytes:
        raise TransportRefusal('non-bytes')
    if len(raw) > BYTE_LIMIT:
        raise TransportRefusal('byte-overflow')
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped: escaped = False
            elif char == 92: escaped = True
            elif char == 34: quoted = False
        elif char == 34: quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > DEPTH_LIMIT:
                raise TransportRefusal('depth-overflow')
        elif char in (93, 125): depth -= 1

def _refuse(receiver, category, reason):
    state = receiver.snapshot()
    record, authority = state['record'], state['authority']
    return {'response': {'kind': category, 'reason': reason},
            'committed': False, 'receipt_lookup_performed': False,
            'state_changed': False, 'record': record,
            'record_revision': record['revision'],
            'authority_epoch': authority['epoch'], 'assignee': authority['assignee'],
            'operation_receipt_count': len(state['operation_receipts']),
            'transfer_receipt_count': len(state['transfer_receipts'])}

def deliver(receiver, kind, raw):
    """Decode one admitted envelope; dispatch the original receiver at most once."""
    if kind not in ('write', 'transfer'):
        raise ValueError('UNSUPPORTED_INGRESS_KIND')
    try:
        _transport(raw)
        envelope = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                              parse_constant=_constant)
        required = 'session presented_epoch intent' if kind == 'write' else 'session intent'
        valid = (fields(envelope, required) and type(envelope['session']) is str
                 and valid_intent(envelope['intent'], kind == 'transfer')
                 and (kind != 'write' or uint(envelope['presented_epoch'])))
        if not valid:
            raise ValueError('invalid-envelope')
    except TransportRefusal as error:
        return _refuse(receiver, 'transport-refusal', str(error))
    except (ValueError, UnicodeError):
        return _refuse(receiver, 'request-refusal', 'invalid-request')
    except RecursionError:
        return _refuse(receiver, 'transport-refusal', 'decoder-resource-limit')
    return receiver.command(kind, envelope['session'], envelope['intent'],
                            envelope.get('presented_epoch'))
