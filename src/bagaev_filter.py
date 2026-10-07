"""Explicit experimental L2/2 pure CLI; no Store or implicit profile conversion."""
import json
import sys
from . import bagaev as transport
from . import bagaev_l2_filter as language
from . import bagaev_l2_filter_backend as backend

SCHEMA='bagaev-filter-toolchain/1'
VERSION='bagaev-filter-toolchain/1 (L2/2; CPython/2; pure only)'

def parser():
    p=transport._Parser(prog='bagaev-filter',description='Explicit experimental pure L2/2 profile')
    p.add_argument('--version',action='version',version=VERSION)
    commands=p.add_subparsers(dest='command',required=True,parser_class=transport._Parser)
    for name in ('check','run','compile','patch','prepare'):
        c=commands.add_parser(name);c.add_argument('program')
        if name=='run':c.add_argument('--input',required=True);c.add_argument('--artifact')
        if name=='patch':c.add_argument('patch')
        if name in ('compile','patch','prepare'):c.add_argument('--output',required=True)
    return p

def execute(a):
    if a.command=='prepare':
        prepared=language.prepare_program(transport._read(a.program,transport.TEXT_LIMIT,'L2_BOUNDS'))
        transport._write_new(a.output,prepared.canonical)
        return {'source':prepared.digest,'bytes':len(prepared.canonical)}
    program=language.check_program(transport._read(a.program,transport.TEXT_LIMIT,'L2_BOUNDS'))
    if a.command=='check':
        value=language.program_value(program)
        return {'source':program.digest,'entry':value['entry'],'definitions':len(value['definitions'])}
    if a.command=='patch':
        changed=language.apply_patch(program,transport._read(a.patch,transport.TEXT_LIMIT,'L2_BOUNDS'))
        if len(changed.canonical)>transport.TEXT_LIMIT:raise transport.ToolError('TOOL_TRANSPORT')
        transport._write_new(a.output,changed.canonical)
        return {'base':program.digest,'source':changed.digest,'bytes':len(changed.canonical)}
    if a.command=='compile':
        artifact=backend.compile_program(program)
        if len(artifact)>backend.ARTIFACT_LIMIT:raise transport.ToolError('TOOL_TRANSPORT')
        metadata=json.loads(artifact);transport._write_new(a.output,artifact)
        return {k:metadata[k] for k in ('source','generator','artifact')}|{'bytes':len(artifact)}
    argument=transport._argument(transport._read(a.input,transport.TEXT_LIMIT,'TOOL_TRANSPORT'))
    if a.artifact is None:result=language.evaluate(program,argument);engine='reference'
    else:
        captured=transport._read(a.artifact,backend.ARTIFACT_LIMIT,'TOOL_TRANSPORT')
        verified=backend.verify_artifact(captured,program)
        namespace={'__name__':'bagaev_filter_compiled'}
        exec(compile(verified,'<bagaev-filter>','exec'),namespace)
        try:result=namespace['evaluate'](argument)
        except namespace['L2RuntimeError'] as e:raise transport.ToolError(e.code,e.location) from None
        engine='cpython'
    return {'source':program.digest,'engine':engine,'value':result}

def main(argv=None):
    command=None
    try:
        a=parser().parse_args(argv);command=a.command
        observation={'schema':SCHEMA,'command':command,'ok':True,'result':execute(a)};status=0
    except (transport.ToolError,language.L2Error,backend.ArtifactError) as e:
        observation={'schema':SCHEMA,'command':command,'ok':False,'error':{'code':e.code,'message':transport._MESSAGES.get(e.code,'Language refusal'),'location':getattr(e,'location',None)}};status=2
    except Exception:
        sys.stderr.write('Filter tool host failure\n');return 1
    print(json.dumps(observation,sort_keys=True,ensure_ascii=True,separators=(',',':')))
    return status

if __name__=='__main__':raise SystemExit(main())
