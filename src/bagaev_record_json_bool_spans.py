"""Explicit form6 expression ranges; descriptive data, no execution admission."""
import bagaev_record_json_bool_form as form
import bagaev_record_wide_spans as prior


class _Reader(prior._Reader, form.Reader):
    # Both readers derive from the same wide Reader. C3 order retains occurrence
    # capture from prior._Reader, then the explicit form6 version/intrinsics.
    pass


def source_map(source):
    expected = form.decode(source)
    result = prior._source_map(source, expected, _Reader)
    result['form'] = 'record-form/6'
    return result
