"""Deterministic discovery data for explicit pure source profiles; no admission."""
import bagaev_record_json_form as narrow
import bagaev_record_wide_form as wide


def describe(version):
    narrow.need(type(version) is str and version in ('4', '5'), 'FORM_VERSION')
    codec = wide if version == '5' else narrow
    profile = 11 if version == '5' else 10
    return {
        'schema': 'bagaev-record-capabilities/1',
        'form': 'record-form/' + version,
        'program_schema': 'bagaev-typed-record/' + str(profile),
        'invocation_schema': 'bagaev-typed-record-invocation/' + str(profile),
        'result_schema': 'bagaev-typed-record-result/' + str(profile),
        'parser_bounds': {'bytes': codec.old.BYTE_LIMIT, 'tokens': codec.old.TOKEN_LIMIT,
                          'values': codec.old.VALUE_LIMIT, 'depth': codec.old.DEPTH_LIMIT},
        'reference_bounds': {'record_list_capacity': 16 if version == '5' else 4,
                             'functions': 32, 'nodes': 2048, 'named_types': 8,
                             'expanded_shape': 4096, 'work': 65536},
        'intrinsic_spellings': [{'name': name, 'arity': arity}
                               for name, arity in sorted(codec.INTRINSICS.items())
                               if name not in ('bool.and', 'bool.or')],
        'intrinsic_scope': 'named-call spellings only; operators and special syntax are not enumerated',
        'literal_arguments': {'json.field': [1], 'record.field': [1], 'records.list': [0]},
        'literal_argument_indexing': 'zero-based; records.list starts with a declared type name',
        'data_tools': {
            'record_text.py': ['decode', 'encode', 'inspect', 'prepare'],
            'record_diagnose.py': ['syntax-context'],
            'record_format.py': ['graph-preserving-format'],
            'record_function.py': ['extract', 'context', 'replace'],
            'record_export.py': ['focused-draft-source']},
        'selection': {'explicit_form_flag': version, 'auto_detection': False},
        'effects': {'source_tools_execute_programs': False, 'pure_program_network': False,
                    'pure_program_filesystem': False, 'durable_state': False},
        'limits_are_not_totality_guarantees': True,
        'semantic_check': False,
        'execution_admission': False,
        'guide': 'docs/record-capabilities.md'}


def describe_v2(version):
    """Explicit additive discovery revision; default describe() remains unchanged."""
    value = describe(version)
    profile = 11 if version == '5' else 10
    value['schema'] = 'bagaev-record-capabilities/2'
    value['data_tools']['record_json_prepare.py'] = ['lossless-json-entry-invocation']
    value['argument_routes'] = {
        'record_text.py': 'strict Int64 numeric transport; typed or Json arguments',
        'record_json_prepare.py': {
            'entry_parameters': 'all Json or zero parameters',
            'argument_shape': 'one JSON array with exact entry arity',
            'numeric_lexemes': 'preserved byte-for-byte without conversion',
            'input_bytes': 1048576, 'invocation_bytes': 1048576,
            'argument_depth': 128, 'duplicate_keys': 'refused',
            'unpaired_surrogates': 'refused', 'non_json_numbers': 'refused',
            'execution_admission': False}}
    value['native_preparation'] = {
        'emitter_source': 'examples/probes/backend/rust/json_native_emit' + str(profile) + '.rs',
        'module_schema': 'bagaev-json-view' + str(profile) + '-llvm-module/1',
        'binding_schema': 'bagaev-json-view' + str(profile) + '-llvm-binding/1',
        'success_wire': 'BCMPRES4' if version == '5' else 'BCMPRES3',
        'target': 'x86_64-unknown-linux-gnu',
        'entry_parameters': 'all Json or zero parameters', 'result_excludes': ['Json'],
        'compiler_invoked': False, 'execution_admission': False,
        'coverage': 'selected conformance only; not a general acceptance guarantee'}
    return value


def describe_v3(version):
    """Explicit discovery of layout-bound debugging data, without execution."""
    value = describe_v2(version)
    value['schema'] = 'bagaev-record-capabilities/3'
    value['source_debugging'] = {'supported': version == '5'}
    if version == '5':
        value['data_tools']['record_source_map.py'] = ['pinned-expression-source-map']
        value['source_debugging'].update({
            'checked_inspector_source': 'examples/probes/backend/rust/json_source_locations11.rs',
            'checked_report_schema': 'bagaev-native-source-locations/1',
            'map_tool': 'tools/record_source_map.py',
            'map_schema': 'bagaev-record-source-map/1',
            'receipt_schema': 'bagaev-record-source-map-receipt/1',
            'required_flags': ['--form', '--program-pin', '--output'],
            'optional_flags': ['--source-sha256', '--pointer'],
            'form_flag_value': '5',
            'program_pin_format': 'sha256: followed by 64 lowercase hex digits',
            'source_sha256_format': '64 lowercase hex digits over exact UTF-8 bytes',
            'join': 'require map program_pin == checked report source_pin, then match program_pointer',
            'pointer_prefix': '/program/functions/',
            'node_ids': 'only from separately checked inspector, never map entry order',
            'byte_ranges': 'half-open UTF-8 offsets',
            'line_columns': 'one-based Unicode scalars; LF starts a line; CR and tab count as scalars',
            'precision': ['exact-expression', 'enclosing-expression'],
            'map_bounds': {'nodes': 2048, 'output_bytes': 1048576},
            'map_semantic_check': False,
            'native_output_authenticated': False,
            'execution_admission': False,
            'guide': 'docs/record-source-map.md'})
    else:
        value['source_debugging']['reason'] = 'combined checked-node/readable-map path is explicit form5 only; no automatic upgrade'
    return value


def describe_v4(version):
    """Explicit discovery of lazy syntax and profile11 prepared/result APIs."""
    value = describe_v3(version)
    value['schema'] = 'bagaev-record-capabilities/4'
    value['profile11_extensions'] = {'supported': version == '5'}
    if version != '5':
        value['profile11_extensions']['reason'] = 'explicit form5 only; does not describe or disable existing profile10 APIs'
        return value
    for name in ('bool.and', 'bool.or'):
        value['intrinsic_spellings'].append({'name': name, 'arity': 2})
    value['intrinsic_spellings'].sort(key=lambda item: item['name'])
    value['intrinsic_scope'] = 'named-call spellings including explicit lazy Boolean surface forms; operators and other special syntax are not enumerated'
    value['profile11_extensions'].update({
        'lazy_boolean_forms': {
            'bool.and': {'arity': 2, 'lowering': 'if left then right else false'},
            'bool.or': {'arity': 2, 'lowering': 'if left then true else right'},
            'both_branches_type_checked': True, 'canonical_spelling': 'if',
            'synthetic_literal_range': 'enclosing-expression'},
        'prepared_reference': {
            'source': 'examples/probes/backend/rust/typed_record.rs',
            'prepare_source': 'prepare_json_program_v11',
            'prepare_arguments': 'prepare_json_arguments_v11',
            'evaluate': 'evaluate_prepared_json_v11',
            'entry_parameters': 'all Json or zero parameters',
            'guide': 'docs/prepared-json11-reference.md'},
        'prepared_native': {
            'source': 'examples/probes/backend/rust/prepared_json_native_v11.rs',
            'prepare_source': 'prepare', 'evaluate': 'evaluate',
            'evaluation_unsafe': True, 'separate_exact_kernel_admission_required': True,
            'actual_scratch_checked_per_call': True, 'result_owned': True,
            'guide': 'docs/prepared-json11-native.md'},
        'success_json_reader': {
            'source': 'examples/probes/backend/rust/native_result_json11_main.rs',
            'library': 'examples/probes/backend/rust/native_result_json_v11.rs',
            'required_flags': ['--source', '--source-pin', '--wire'],
            'wire': 'BCMPRES4', 'result_schema': 'bagaev-native-result/11',
            'unbound_failure_packets': 'refused', 'source_or_kernel_execution': False,
            'output_file_writes': False, 'origin_authenticated': False,
            'guide': 'docs/native-result-json11.md'},
        'execution_admission': False,
        'performance_claim': False})
    return value
