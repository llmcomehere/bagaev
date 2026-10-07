"""Explicit bounded-test executable selection; hashes identify bytes, not authority."""
from pathlib import Path
import argparse,hashlib,re
def configure(*,reference=False,matcher=False,qualification=False):
 p=argparse.ArgumentParser(description='Run finite outcome checks with separately reviewed host executables.')
 p.add_argument('--output',required=True,type=Path)
 if qualification:
  p.add_argument('--qualification-directory',required=True,type=Path)
  for name in ('producer','good','bad'):p.add_argument('--'+name+'-sha256',required=True)
 for name,needed in [('reader',True),('reference',reference),('matcher',matcher)]:
  if needed:p.add_argument('--'+name,required=True,type=Path);p.add_argument('--'+name+'-sha256',required=True)
 a=p.parse_args();out=a.output
 assert out.is_absolute() and out.parent.is_dir() and not out.exists()
 if qualification:
  assert a.qualification_directory.is_absolute() and a.qualification_directory.is_dir()
  for name in ('producer','good','bad'):assert re.fullmatch('[0-9a-f]{64}',getattr(a,name+'_sha256'))
 for name,needed in [('reader',True),('reference',reference),('matcher',matcher)]:
  if not needed:continue
  f=getattr(a,name);h=getattr(a,name+'_sha256')
  assert f.is_absolute() and f.is_file() and not f.is_symlink() and re.fullmatch('[0-9a-f]{64}',h)
  assert hashlib.sha256(f.read_bytes()).hexdigest()==h
 return a
