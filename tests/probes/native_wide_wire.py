"""Structural extraction of Rust-validated BCMPRES4 bytes; no application logic."""
import struct

def decode(program,wire,binding):
    assert wire[:8]==b'BCMPRES4' and wire[24:56]==binding and wire[56:64]==bytes(8)
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

