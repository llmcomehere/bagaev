"""Structural extraction of Rust-validated BCMPRES1 bytes; no application logic."""
import struct

def decode(program,wire,binding):
    assert wire[:8]==b'BCMPRES1' and wire[24:56]==binding and wire[56:64]==bytes(8)
    count,text_bytes,work=struct.unpack_from('<IIQ',wire,8)
    assert 1<=count<=4096 and text_bytes<=4194304 and work<=65536
    pool=64+count*32;assert len(wire)==pool+text_bytes
    records=sorted(program['records']);lists=sorted(program['lists']);variants=sorted(program['variants'])
    used=0
    def node(ty,i):
        nonlocal used
        assert 0<=i<count
        tag,nominal,scalar,end,n,offset,length=struct.unpack_from('<IIqIIII',wire,64+32*i)
        assert i<end<=count
        if tag!=3:assert offset==length==0
        next_i=i+1
        if ty in records:
            fields=program['records'][ty];assert tag==6 and nominal==records.index(ty) and scalar==0 and n==len(fields);value={}
            for name,spec in sorted(fields.items()):
                optional=isinstance(spec,dict);ft=spec['type'] if optional else spec;v,next_i=node(ft,next_i)
                if not(optional and v is None):value[name]=v
        elif ty in lists:
            spec=program['lists'][ty];assert tag==7 and nominal==len(records)+lists.index(ty) and scalar==0 and n<=spec['capacity'];value=[]
            for _ in range(n):v,next_i=node(spec['element'],next_i);value.append(v)
        elif ty in variants:
            alts=sorted(program['variants'][ty]);assert tag==8 and nominal==len(records)+len(lists)+variants.index(ty) and n==1 and 0<=scalar<len(alts);case=alts[scalar];v,next_i=node(program['variants'][ty][case],next_i);value={'case':case,'value':v}
        elif ty=='Text':
            assert tag==3 and nominal==scalar==n==0 and offset==used and length<=1024
            value=wire[pool+offset:pool+offset+length].decode();assert len(value)<=256 and offset+length<=text_bytes;used+=length
        elif ty=='TextList':
            assert tag==5 and nominal==scalar==0 and n<=64;before=used;value=[]
            for _ in range(n):v,next_i=node('Text',next_i);value.append(v)
            assert used-before<=4096
        elif ty=='OptionInt64':assert nominal==n==0 and tag in (4,9);assert tag!=4 or scalar==0;value=None if tag==4 else scalar
        elif ty=='Int64':assert tag==1 and nominal==n==0;value=scalar
        elif ty=='Bool':assert tag==2 and nominal==n==0 and scalar in (0,1);value=bool(scalar)
        else:raise AssertionError(ty)
        assert next_i==end
        return value,next_i
    value,end=node(program['functions'][program['entry']]['result'],0)
    assert end==count and used==text_bytes
    return value,work


def main():
    import argparse,copy,hashlib,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description="Data-only native catalogue fixtures and result checks; never compile or execute kernels")
    parser.add_argument("mode",choices=["request","check"]);parser.add_argument("case")
    parser.add_argument("--output",type=Path);parser.add_argument("--previous",type=Path)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    source=(root/"examples/probes/catalog-source/program.json").read_bytes()
    raw=(root/"examples/beta/catalog-cases.json").read_bytes()
    observation=json.loads((root/"examples/probes/native-json/catalog-observations.json").read_text())
    binding=hashlib.sha256(source).digest()
    if binding.hex()!=observation["source_sha256"] or hashlib.sha256(raw).hexdigest()!=observation["oracle_sha256"]:raise ValueError("fixture/source version mismatch")
    program=json.loads(source);oracle=json.loads(raw);index={c["id"]:c for c in oracle["cases"]}
    case=index[args.case]
    def same(a,z):
        if type(a)!=type(z):return False
        if isinstance(a,dict):return a.keys()==z.keys() and all(same(a[k],z[k]) for k in a)
        if isinstance(a,list):return len(a)==len(z) and all(same(x,y) for x,y in zip(a,z))
        return a==z
    def checked(ident,path):
        if path.is_symlink() or not path.is_file():raise ValueError("result must be a regular file")
        with path.open("rb") as f:wire=f.read(4325441)
        if len(wire)>4325440:raise ValueError("result exceeds bound")
        wrapper,work=decode(program,wire,binding);expected=oracle["responses"][index[ident]["expect"]]
        if wrapper["case"]!=("Ok" if expected["kind"]=="success" else "Error") or not same(wrapper["value"],expected) or work!=observation["logical_work"][ident]:raise ValueError("complete response/work mismatch")
        return wrapper["value"],work
    if args.mode=="request":
        if args.output is not None:raise ValueError("request emits stdout only")
        request=copy.deepcopy(oracle["requests"][case["request"]])
        if args.previous is not None:
            chain=next(c["cases"] for c in oracle["chains"] if args.case in c["cases"]);at=chain.index(args.case)
            if at==0:raise ValueError("first chain step has no predecessor")
            prior,_=checked(chain[at-1],args.previous)
            if not same(prior["state"],request["state"]):raise ValueError("chain state mismatch")
            request["state"]=copy.deepcopy(prior["state"])
        print(json.dumps({"schema":"bagaev-typed-record-invocation/8","program":program,"arguments":[request]},ensure_ascii=True,separators=(",",":")))
    else:
        if args.output is None or args.previous is not None:raise ValueError("check requires --output only")
        _,work=checked(args.case,args.output);print(json.dumps({"case":args.case,"complete_response":True,"logical_work":work,"measurement":False}))

if __name__=="__main__":main()
