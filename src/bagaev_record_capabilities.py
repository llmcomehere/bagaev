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
                               for name, arity in sorted(codec.INTRINSICS.items())],
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
