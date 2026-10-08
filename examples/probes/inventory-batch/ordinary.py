"""Independent ordinary Python value oracle for the frozen bounded batch contract."""
import copy


def integer(value):
    return type(value) is int and -(1 << 63) <= value < (1 << 63)


def object_keys(value, keys):
    return type(value) is dict and set(value) == set(keys)


def item_shape(value):
    return object_keys(value, ('sku', 'available')) and type(value['sku']) is str and integer(value['available'])


def request_shape(value):
    return object_keys(value, ('sku', 'amount')) and type(value['sku']) is str and integer(value['amount'])


def sku_ok(value):
    return 1 <= len(value.encode('utf8')) <= 32


def stock_ok(items):
    return all(sku_ok(item['sku']) and item['available'] >= 0 for item in items) and len({x['sku'] for x in items}) == len(items)


def reject(step, reason, items):
    return {'case': 'BatchRejected', 'value': {'step': step, 'reason': reason, 'stock': copy.deepcopy(items)}}


def batch(value):
    if not (object_keys(value, ('interface', 'stock', 'requests'))
            and value['interface'] == 'inventory-batch/1'
            and type(value['stock']) is list and len(value['stock']) <= 16
            and all(item_shape(x) for x in value['stock'])
            and type(value['requests']) is list and len(value['requests']) <= 4
            and all(request_shape(x) for x in value['requests'])):
        return reject(-1, 'request-shape', [])
    original = value['stock']
    current = copy.deepcopy(original)
    receipts = []
    if not value['requests'] and not stock_ok(original):
        return reject(-1, 'invalid-stock', original)
    for step, request in enumerate(value['requests']):
        sku, amount = request['sku'], request['amount']
        if amount < 1 or not sku_ok(sku):return reject(step, 'invalid-request', original)
        if amount > 5:return reject(step, 'order-limit', original)
        if not stock_ok(current):return reject(step, 'invalid-stock', original)
        matches = [i for i, item in enumerate(current) if item['sku'] == sku]
        if not matches:return reject(step, 'not-found', original)
        index = matches[0]
        if current[index]['available'] < amount:return reject(step, 'insufficient-stock', original)
        current[index]['available'] -= amount
        receipts.append({'stock': copy.deepcopy(current), 'sku': sku, 'amount': amount})
    return {'case': 'BatchCommitted', 'value': {'stock': current, 'receipts': receipts}}
