"""Explicit data-only record-form/6 for typed-record/12; no execution admission."""
import bagaev_record_wide_form as prior
FormError=prior.FormError
INTRINSICS={**prior.INTRINSICS,'json.bool_or':2}
class Reader(prior.Reader):
    version='6';schema='bagaev-typed-record/12';intrinsics=INTRINSICS

def decode(source):
    try:return Reader(source).read()
    except RecursionError:raise FormError('FORM_BOUNDS') from None

def encode(value):
    return prior._encode(value,False,schema=Reader.schema,version=Reader.version,intrinsics=INTRINSICS,decoder=decode)

def encode_named(value):
    return prior._encode(value,True,schema=Reader.schema,version=Reader.version,intrinsics=INTRINSICS,decoder=decode)
