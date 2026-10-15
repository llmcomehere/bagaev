"""Join supplied scalar failure data to a pinned form5 expression; never evaluate."""
import re
from bagaev_record_capture_compare import compare_captures
from bagaev_record_draft import need, digest
from bagaev_record_wide_spans import source_map


def locate_failure(source, capture, *, program_sha256, arguments_sha256,
                   source_sha256):
    """Pins bind supplied data, not its authenticity or semantic correctness."""
    checked = compare_captures(capture, capture, base_sha256=program_sha256,
                               target_sha256=program_sha256,
                               arguments_sha256=arguments_sha256)
    result = capture['result']
    need(result['status'] != 'success', 'DIAGNOSTIC_STATUS')
    need(type(source_sha256) is str and
         re.fullmatch('[0-9a-f]{64}', source_sha256) is not None,
         'DIAGNOSTIC_LAYOUT')
    mapping = source_map(source)
    need(mapping['program_pin'] == 'sha256:' + program_sha256,
         'DIAGNOSTIC_PROGRAM')
    need(mapping['source_sha256'] == source_sha256, 'DIAGNOSTIC_LAYOUT')
    selected = [entry for entry in mapping['locations']
                if entry['program_pointer'] == result['location']]
    need(len(selected) == 1, 'DIAGNOSTIC_POINTER')
    location = selected[0]
    raw = source.encode('utf8') if type(source) is str else source
    excerpt = raw[location['start_byte']:location['end_byte']].decode('utf8')
    return dict(schema='bagaev-record-failure-location/1',
                program_sha256=program_sha256, arguments_sha256=arguments_sha256,
                source_sha256=source_sha256, capture_sha256=digest(capture),
                result_sha256=checked['before_result_sha256'],
                result=dict(result), location=dict(location),
                excerpt=excerpt[:256], excerpt_truncated=len(excerpt) > 256,
                semantic_check=False, capture_authentication=False,
                execution_admission=False)
