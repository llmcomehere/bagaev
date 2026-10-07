"""Explicit form/6 change frame using unchanged source/2 draft rules."""
import bagaev_component_outcome_edit as shared
import bagaev_component_fold_form as form
EditError=shared.EditError
CheckerUnavailable=shared.CheckerUnavailable
ComponentRefused=shared.ComponentRefused
canonical=shared.canonical
digest=shared.digest
def frame(source):
 return shared._frame(source,schema='component-edit/6',form_name='component-form/6')
def draft(original,edit_frame,policy,checker,*,candidate_map=None):
 before=form.decode(original)
 base=shared.checked(before,policy,checker,'base')
 request=frame(edit_frame)
 after=form.decode(request['source'])
 return shared._draft_values(before,request,after,policy,checker,base,candidate_map=candidate_map)
