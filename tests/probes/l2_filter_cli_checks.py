"""Own actual subprocess checks of the explicit /2 CLI and unchanged /1."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/l2-filter'
sys.path.insert(0,str(T))
from src import bagaev_l2_filter as language
from src import bagaev_l2 as old
from src import bagaev_l2_backend as old_backend

def document(body,version):
    definition={'params':['x'],'body':body}
    raw=json.dumps({'schema':f'bagaev-l2-definition/{version}','definition':definition,'dependencies':{}},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return {'schema':f'bagaev-l2/{version}','entry':'main','definitions':{'main':definition},'pins':{'main':'sha256:'+hashlib.sha256(raw).hexdigest()}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
    assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir();rows=[]
    p2=document(['filter',['var','x'],'item',['get',['var','item'],'keep']],2);p1=document(['var','x'],1)
    def write(name,value):
        p=R/name;p.write_bytes(value if type(value)is bytes else json.dumps(value).encode());return str(p)
    source=write('source.json',p2);prior=write('old.json',p1)
    argument=write('input.json',[{'keep':False,'id':'closed'},{'keep':True,'id':'open'}]);artifact=str(R/'artifact.json')
    def cli(args,error=None,legacy=False):
        q=subprocess.run([sys.executable,'-B','-S','-m','src.bagaev' if legacy else 'src.bagaev_filter',*args],cwd=T,capture_output=True,timeout=20)
        i=len(rows);(R/f'{i:02d}.stdout').write_bytes(q.stdout);(R/f'{i:02d}.stderr').write_bytes(q.stderr)
        assert q.returncode==(2 if error else 0) and not q.stderr,(args,q.returncode,q.stderr,q.stdout)
        v=json.loads(q.stdout);assert v['ok'] is (error is None)
        assert v['schema']==('bagaev-toolchain/1' if legacy else 'bagaev-filter-toolchain/1')
        if error:assert v['error']['code']==error
        rows.append({'args':args,'expected_error':error,'observation':v});return v.get('result')
    cli(['check',source]);cli(['check',prior],legacy=True)
    wanted=[{'keep':True,'id':'open'}]
    assert cli(['run',source,'--input',argument])['value']==wanted
    cli(['compile',source,'--output',artifact]);assert json.loads(Path(artifact).read_bytes())['schema']=='bagaev-l2-cpython/2'
    assert cli(['run',source,'--input',argument,'--artifact',artifact])['value']==wanted
    cli(['check',prior],'L2_PROGRAM');cli(['check',source],'L2_PROGRAM',legacy=True)
    tampered=write('tampered.json',Path(artifact).read_bytes()+b' ')
    foreign=write('foreign-artifact.json',old_backend.compile_program(p1))
    for bad in (tampered,foreign):cli(['run',source,'--input',argument,'--artifact',bad],'TOOL_ARTIFACT')
    patch=language.prepare_patch(p2,{}, {'main':{'params':['x'],'body':['filter',['var','x'],'item',False]}})
    patchpath=write('change.patch',patch);updated=str(R/'updated.json')
    cli(['patch',source,patchpath,'--output',updated]);assert cli(['run',updated,'--input',argument])['value']==[]
    stale=str(R/'stale.json');cli(['patch',updated,patchpath,'--output',stale],'L2_STALE');assert not Path(stale).exists()
    oldpatch=write('old.patch',old.prepare_patch(p1,{}, {'main':{'params':['x'],'body':0}}))
    cli(['patch',source,oldpatch,'--output',stale],'L2_PATCH');assert not Path(stale).exists()
    invalid=write('invalid.json',b'{');cli(['check',invalid],'L2_JSON')
    dupe=write('duplicate.json',b'[{"keep":true,"keep":false}]');cli(['run',source,'--input',dupe],'TOOL_TRANSPORT')
    link=R/'source-link.json';link.symlink_to(Path(source));cli(['check',str(link)],'TOOL_INPUT')
    existing=write('existing.json',b'preserve');cli(['compile',source,'--output',existing],'TOOL_OUTPUT');assert Path(existing).read_bytes()==b'preserve'
    cli(['store','init','unused'],'TOOL_USAGE');assert not (T/'unused').exists()
    before=json.loads((D/'legacy-modules.json').read_bytes())['sha256'];assert all(hashlib.sha256((T/n).read_bytes()).hexdigest()==h for n,h in before.items())
    result={'status':'PASSED','cli_calls':len(rows),'intentional_refusals':sum(r['expected_error'] is not None for r in rows),'old_files_unchanged':len(before),'rows':rows}
    (R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))

if __name__=='__main__':main()
