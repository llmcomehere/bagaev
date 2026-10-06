"""Synthetic literal fixture materialization; no file or executable admission."""
import copy,hashlib,json

def sha(data):
    return hashlib.sha256(data).hexdigest()

def base():
    content = {k: (k + '-literal').encode() for k in ('source', 'module', 'harness', 'artifact')}
    rec = {'schema': 'bagaev-build-record-inspection/1', 'profile': 8,
           **{k: sha(v) for k, v in content.items()},
           'build': {'target': 'x86_64-unknown-linux-gnu', 'llvm_opt': 'O2',
                     'rust_opt': 'default-unspecified', 'clang': 'c' * 64, 'rustc': 'd' * 64},
           'dependencies': {'needed': ['libc.so.6'], 'interpreter': '/synthetic/loader',
                            'search_path': [], 'versions': ['GLIBC_2.34']},
           'provenance': 'retrospective-association'}
    return rec, content

def set_at(record, path, value):
    for key in path[:-1]:
        record = record[key]
    record[path[-1]] = value

def materialize(case):
    rec, content = base()
    expected = copy.deepcopy(rec)
    for key, value in case.get('both', []):
        rec[key] = expected[key] = value
    for path, value in case.get('record_set', []):
        set_at(rec, path, value)
    if case.get('expected_absent'):
        expected = None
    if 'bytes_change' in case:
        content[case['bytes_change']] += b'x'
    if 'bytes_missing' in case:
        del content[case['bytes_missing']]
    if 'bytes_mutable' in case:
        key = case['bytes_mutable']; content[key] = bytearray(content[key])
    if 'bytes_bound' in case:
        key = case['bytes_bound']; cap = {'source': 1048576, 'module': 8388608, 'harness': 1048576, 'artifact': 33554432}[key]
        content[key] = b'x' * (cap + 1)
    raw = json.dumps(rec).encode()
    mode = case.get('raw')
    if mode == 'duplicate-escaped':
        raw = raw[:-1] + b',"\\u0070rofile":8}'
    elif mode == 'utf8': raw = b'\xff'
    elif mode == 'bom': raw = b'\xef\xbb\xbf' + raw
    elif mode == 'trailing': raw += b' {}'
    elif mode == 'oversize': raw = b' ' * 65537
    return raw, expected, content

