"""Explicit component-context/1 inspection. No discovery, model exchange or admission."""
import copy
import bagaev_probe_context as common
ContextError=common.ContextError
ContextUnavailable=common.ContextUnavailable
class ComponentRefusal(common.KernelRefusal):
    """Actual trusted component checker refusal, with context-relative location."""
def inspect(context,expectation,*,component_checker=None):
    """Reconstruct pinned component context using a separately configured checker.

    The checker must completely check the component against independently supplied
    receiving policy and return its exact canonical bytes. It is never packet data.
    This API only inspects context; it cannot execute, select a model or grant rights.
    """
    try:value,expected,_,_=common._validate(context,expectation,component_checker,component=True)
    except common.KernelRefusal as error:raise ComponentRefusal(error.code,error.location) from None
    return {'schema':'component-context-inspection/1','snapshot':value['snapshot'],
            'candidate_set':value['candidate_set'],'unknowns':[x['id'] for x in value['unknowns']],
            'open_effects':[x['id'] for x in value['open_effects']],
            'programme_sources':copy.deepcopy(expected['programme_sources']),
            'admission':False,'model_calls':0}
