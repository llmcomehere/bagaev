"""Locate supplied input-bound semantic refusals; no checking or execution."""
import hashlib
import json
import re
from bagaev_record_draft import need, digest, DraftError
import bagaev_record_wide_form as form
from bagaev_record_wide_spans import source_map


def _raw(value):
    need(type(value) in (str, bytes), 'CHECK_LOCATION_INPUT')
    try:
        raw = value.encode('utf8') if type(value) is str else value
        need(len(raw) <= 1048576, 'CHECK_LOCATION_BOUNDS')
        raw.decode('utf8')
    except UnicodeError:
        raise DraftError('CHECK_LOCATION_INPUT') from None
    return raw


def _json(raw):
    depth, quoted, escaped = 0, False, False
    for byte in raw:
        if quoted:
            if escaped: escaped = False
            elif byte == 92: escaped = True
            elif byte == 34: quoted = False
        elif byte == 34: quoted = True
        elif byte in (91, 123):
            depth += 1
            need(depth <= 128, 'CHECK_LOCATION_BOUNDS')
        elif byte in (93, 125): depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'CHECK_LOCATION_JSON')
            result[key] = value
        return result
    def integer(text):
        need(len(text) <= 20, 'CHECK_LOCATION_JSON')
        value = int(text)
        need(-(1<<63) <= value < (1<<63), 'CHECK_LOCATION_JSON')
        return value
    def reject(text):
        raise DraftError('CHECK_LOCATION_JSON')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_int=integer,
                           parse_float=reject, parse_constant=reject)
        # Includes rejection of lone surrogate escapes throughout the tree.
        digest(value)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        if isinstance(error, DraftError): raise
        raise DraftError('CHECK_LOCATION_JSON') from None


def locate(source, checked_input, result_bytes, *, source_sha256,
           program_sha256, input_sha256, result_sha256):
    return _locate(source, checked_input, result_bytes, source_sha256=source_sha256,
        program_sha256=program_sha256, input_sha256=input_sha256, result_sha256=result_sha256,
        codec=form, mapper=source_map, profile='11', version='1')


def locate_form6(source, checked_input, result_bytes, *, source_sha256,
                 program_sha256, input_sha256, result_sha256):
    import bagaev_record_json_bool_form as form6
    from bagaev_record_json_bool_spans import source_map as map6
    return _locate(source, checked_input, result_bytes, source_sha256=source_sha256,
        program_sha256=program_sha256, input_sha256=input_sha256, result_sha256=result_sha256,
        codec=form6, mapper=map6, profile='12', version='2')


def _locate(source, checked_input, result_bytes, *, source_sha256,
            program_sha256, input_sha256, result_sha256, codec, mapper, profile, version):
    for pin in (source_sha256, program_sha256, input_sha256, result_sha256):
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin) is not None,
             'CHECK_LOCATION_PIN')
    raw, submitted, retained = map(_raw, (source, checked_input, result_bytes))
    for value, pin, code in ((raw, source_sha256, 'CHECK_LOCATION_LAYOUT'),
                            (submitted, input_sha256, 'CHECK_LOCATION_INPUT_PIN'),
                            (retained, result_sha256, 'CHECK_LOCATION_RESULT_PIN')):
        need(hashlib.sha256(value).hexdigest() == pin, code)
    program = codec.decode(raw)
    need(digest(program) == program_sha256 and digest(_json(submitted)) == program_sha256,
         'CHECK_LOCATION_PROGRAM')
    result = _json(retained)
    need(type(result) is dict and set(result) == {'schema','status','program_sha256',
         'input_sha256','reason','location','execution_admission'}, 'CHECK_LOCATION_RESULT')
    need(result['schema'] == 'bagaev-record-source-check/'+profile and result['status'] == 'refused'
         and result['program_sha256'] is None and result['execution_admission'] is False,
         'CHECK_LOCATION_RESULT')
    need(result['input_sha256'] == input_sha256, 'CHECK_LOCATION_BINDING')
    reason, pointer = result['reason'], result['location']
    need(type(reason) is str and reason in {'RR_JSON','RR_VERSION','RR_SHAPE','RR_BOUNDS',
         'RR_REFERENCE','RR_CYCLE','RR_TYPE','RR_ARGUMENT'}, 'CHECK_LOCATION_RESULT')
    need(type(pointer) is str and len(pointer) <= 4096 and
         (pointer == '' or re.fullmatch(r'/(?:[^~\x00-\x1f]|~[01])*', pointer) is not None),
         'CHECK_LOCATION_POINTER')
    mapping = mapper(raw)
    need(mapping['program_pin'] == 'sha256:'+program_sha256 and
         mapping['source_sha256'] == source_sha256, 'CHECK_LOCATION_PROGRAM')
    locations = [row for row in mapping['locations'] if row['program_pointer'] == '/program'+pointer]
    mapped = reason in ('RR_TYPE','RR_REFERENCE') and len(locations) == 1
    location = dict(locations[0]) if mapped else None
    excerpt = raw[location['start_byte']:location['end_byte']].decode('utf8') if mapped else None
    return {'schema':'bagaev-record-check-location/'+version,'status':'mapped' if mapped else 'unmapped',
            'source_sha256':source_sha256,'program_sha256':program_sha256,
            'input_sha256':input_sha256,'result_sha256':result_sha256,
            'reason':reason,'checker_pointer':pointer,'location':location,
            'excerpt':excerpt[:256] if mapped else None,
            'excerpt_truncated':len(excerpt)>256 if mapped else False,
            'semantic_check':False,'result_authentication':False,'execution_admission':False}
