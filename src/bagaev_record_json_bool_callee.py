"""Explicit pinned-base named-callee lowering for a detached form6 fragment."""
from bagaev_record_wide_function import _context_reader
from bagaev_record_json_bool_change import form, digest, need, replace


def replace_in_context(source, replacement, *, base_sha256, function_sha256):
    """Use only base parameter names; unchanged focused receiver checks the draft."""
    program = form.decode(source)
    need(type(base_sha256) is str and digest(program) == base_sha256, 'FUNCTION_BASE')
    reader = _context_reader(form.Reader, program)
    try:
        part = reader(replacement).read()
    except RecursionError:
        raise form.FormError('FORM_BOUNDS') from None
    return replace(source, form.encode(part), base_sha256=base_sha256,
                   function_sha256=function_sha256)
