"""Pure partial build-record association. No execution or build attestation."""
import hashlib
import json
import re

KEYS = {'schema', 'profile', 'source', 'module', 'harness', 'artifact',
        'build', 'dependencies', 'provenance'}
CONTENT = ('source', 'module', 'harness', 'artifact')
LIMITS = (1048576, 8388608, 1048576, 33554432)
PIN = re.compile(r'[0-9a-f]{64}\Z')

class Refusal(ValueError):
    pass

def fields(value, names):
    return type(value) is dict and set(value) == set(names)

def pin(value):
    return type(value) is str and PIN.fullmatch(value) is not None

def ascii_text(value, limit):
    return type(value) is str and 1 <= len(value) <= limit and all(32 <= ord(c) <= 126 for c in value)

def names(value):
    return (type(value) is list and len(value) <= 32
            and all(ascii_text(v, 128) for v in value)
            and value == sorted(set(value)))

def shape(value):
    if not fields(value, KEYS):
        return False
    if type(value['schema']) is not str or value['schema'] != 'bagaev-build-record-inspection/1' or type(value['profile']) is not int or value['profile'] != 8:
        return False
    if not all(pin(value[k]) for k in CONTENT):
        return False
    build = value['build']
    if not fields(build, {'target', 'llvm_opt', 'rust_opt', 'clang', 'rustc'}):
        return False
    if not all(type(build[k]) is str for k in ('target', 'llvm_opt', 'rust_opt')):
        return False
    if (build['target'] != 'x86_64-unknown-linux-gnu' or build['llvm_opt'] not in ('O0', 'O2')
            or build['rust_opt'] != 'default-unspecified' or not pin(build['clang']) or not pin(build['rustc'])):
        return False
    dep = value['dependencies']
    if not fields(dep, {'needed', 'interpreter', 'search_path', 'versions'}):
        return False
    if not names(dep['needed']) or not names(dep['versions']) or not ascii_text(dep['interpreter'], 256):
        return False
    if type(dep['search_path']) is not list or dep['search_path']:
        return False
    return type(value['provenance']) is str and value['provenance'] in ('retrospective-association', 'observed-build')

def no_number(_):
    raise Refusal('FORMAT')

def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise Refusal('FORMAT')
        value[key] = item
    return value

def inspect(raw, expected, content):
    if type(raw) is not bytes:
        raise Refusal('FORMAT')
    if len(raw) > 65536:
        raise Refusal('BOUND')
    try:
        record = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                            parse_float=no_number, parse_constant=no_number)
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal('FORMAT') from None
    if not shape(expected):
        raise Refusal('EXPECTED')
    if not shape(record):
        raise Refusal('SHAPE')
    for key in ('profile', 'build', 'dependencies', 'provenance'):
        if record[key] != expected[key]:
            raise Refusal('CONTEXT')
    for key in CONTENT:
        if record[key] != expected[key]:
            raise Refusal('PIN')
    if not fields(content, CONTENT):
        raise Refusal('BYTES')
    for key, limit in zip(CONTENT, LIMITS):
        if type(content[key]) is not bytes:
            raise Refusal('BYTES')
        if len(content[key]) > limit:
            raise Refusal('BOUND')
    for key in CONTENT:
        if hashlib.sha256(content[key]).hexdigest() != record[key]:
            raise Refusal('CONTENT')
    return {'status': 'matched-data', 'execution_admission': False,
            'build_verified': False, 'dependencies_resolved': False}
