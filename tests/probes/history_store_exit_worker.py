"""One own-store append terminated at a named transaction boundary; no background work."""
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('control',type=Path);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--stage',choices=('before_commit','after_commit'),required=True);a=p.parse_args()
assert not a.output_root.is_symlink() and a.output_root.is_dir()
sandbox=a.output_root.resolve(strict=True)
assert not a.control.is_symlink() and a.control.resolve().is_relative_to(sandbox) and a.control.stat().st_size<=4096
control=json.loads(a.control.read_bytes());assert set(control)=={'directory','form','package_sha256','head','source','source_sha256','program_sha256'}
assert Path(control['directory']).resolve().is_relative_to(sandbox) and Path(control['source']).resolve().is_relative_to(sandbox)
assert Path(control['directory']).parent.resolve()==a.control.parent.resolve() and Path(control['source']).parent.resolve()==a.control.parent.resolve()
assert hashlib.sha256((ROOT/'tools/record_history_store.py').read_bytes()).hexdigest()=='0d4ddfbe178894d824199905c52aeafd84f3581cce182a9995966a0ed4f9b666'
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'src'));import record_history_store as store
def event(stage):
 if stage==a.stage:os._exit(73 if stage=='before_commit' else 74)
store._event=event
store.append(**control)
raise AssertionError('exit boundary was not reached')
