"""Synthetic inert-rendering and no-overwrite checks; no example execution."""
from pathlib import Path
import hashlib,importlib.util,json,tempfile,unittest
from html.parser import HTMLParser
P=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('owned_offline_docs',P/'tools/build_offline_docs.py');B=importlib.util.module_from_spec(s);s.loader.exec_module(B)
REV='a'*40
class Tags(HTMLParser):
 def __init__(self):super().__init__();self.tags=[];self.links=[];self.code=[];self.in_code=False
 def handle_starttag(self,tag,attrs):
  self.tags.append(tag);attrs=dict(attrs)
  if tag=='a':self.links.append(attrs['href'])
  if tag=='code':self.in_code=True
 def handle_endtag(self,tag):
  if tag=='code':self.in_code=False
 def handle_data(self,text):
  if self.in_code:self.code.append(text)
class OfflineDocsTests(unittest.TestCase):
 def fixture(self,root,text='# Example\n\nSome text.\n'):
  root.mkdir()
  for n in B.SOURCES:
   p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 def test_deterministic_and_provenance(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);root=p/'source';self.fixture(root);B.build(root,p/'one',REV);B.build(root,p/'two',REV)
   a={f.relative_to(p/'one').as_posix():f.read_bytes() for f in (p/'one').rglob('*') if f.is_file()};b={f.relative_to(p/'two').as_posix():f.read_bytes() for f in (p/'two').rglob('*') if f.is_file()};self.assertEqual(a,b);self.assertEqual(len(a),29)
   m=json.loads(a['index.json']);self.assertEqual(len(m['sources']),27)
   for r in m['sources']:
    self.assertEqual(r['sha256'],hashlib.sha256((root/r['source']).read_bytes()).hexdigest());self.assertIn('/'+REV+'/',r['source_url']);self.assertIn(r['page'],a)
 def test_saved_workflow_local_routes(self):
  self.assertEqual(B.link('filter-saved-workflow.md','docs/choose-and-start.md',REV),'filter-saved-workflow.html')
  self.assertEqual(B.link('store.md','docs/filter-saved-workflow.md',REV),'store.html')
  self.assertEqual(B.link('pure-filter.md','docs/filter-saved-workflow.md',REV),'pure-filter.html')
  self.assertEqual(B.link('../tests/probes/filter_workflow_checks.py','docs/filter-saved-workflow.md',REV),B.REPOSITORY+'/blob/'+REV+'/tests/probes/filter_workflow_checks.py')
 def test_stateful_component_local_routes(self):
  self.assertEqual(B.link('stateful-components.md','docs/choose-and-start.md',REV),'stateful-components.html')
  for name in ('probe-component-outcomes','probe-outcome-composition','probe-outcome-persistence'):
   self.assertEqual(B.link(name+'.md','docs/stateful-components.md',REV),name+'.html')
 def test_readable_language_local_routes(self):
  for name in ('component-text-cli', 'component-arithmetic-form', 'component-arithmetic-edits', 'component-diagnostics', 'readable-authoring', 'component-match-form', 'component-match-edits', 'stock-adjustment', 'component-expression-locations', 'component-text-list-form', 'tag-box', 'component-fold-form', 'tag-box-budget'):
   self.assertEqual(B.link(name+'.md','docs/readable-authoring.md',REV),name+'.html')
 def test_inert_code_and_raw_html(self):
  code='<script>alert("x")</script> & [link](javascript:x)\n';body,title=B.render('# Example\n\n```text\n'+code+'```\n\n<img src=x onerror=alert(1)>\n','README.md',REV);parser=Tags();parser.feed(body);self.assertNotIn('script',parser.tags);self.assertNotIn('img',parser.tags);self.assertEqual(''.join(parser.code),code)
 def test_link_routes(self):
  self.assertEqual(B.link('pure-filter.md#stable-selection','docs/beta.md',REV),'pure-filter.html#stable-selection');self.assertEqual(B.link('../src/bagaev.py','docs/beta.md',REV),B.REPOSITORY+'/blob/'+REV+'/src/bagaev.py');self.assertEqual(B.link('#example','README.md',REV),'#example')
 def test_unsafe_links_refuse_before_output(self):
  for target in ('javascript:alert','data:text/plain,x','file:///tmp/x','//example.com','../private','%2e%2e/private'):
   with self.subTest(target=target),tempfile.TemporaryDirectory() as d:
    p=Path(d);root=p/'source';self.fixture(root,'# Example\n\n[x]('+target+')\n');out=p/'output'
    with self.assertRaises(B.BuildError):B.build(root,out,REV)
    self.assertFalse(out.exists())
 def test_bad_source_revision_existing_output(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);root=p/'source';self.fixture(root);out=p/'output'
   with self.assertRaises(B.BuildError):B.build(root,out,'main')
   self.assertFalse(out.exists());(root/'README.md').unlink()
   with self.assertRaises(B.BuildError):B.build(root,out,REV)
   self.assertFalse(out.exists());(root/'README.md').symlink_to(root/'LICENSE')
   with self.assertRaises(B.BuildError):B.build(root,out,REV)
   self.assertFalse(out.exists());(root/'README.md').unlink();(root/'README.md').write_text('# Example\n');out.mkdir();(out/'keep').write_text('preserve')
   with self.assertRaises(B.BuildError):B.build(root,out,REV)
   self.assertEqual((out/'keep').read_text(),'preserve')
 def test_nested_lists_and_numbers(self):
  body,_=B.render('# Example\n\n- parent\n  - child\n- sibling\n\n4. fourth\n5. fifth\n','README.md',REV)
  self.assertIn('<li>parent<ul><li>child</li></ul></li>',body)
  self.assertIn('<li value="4">fourth</li>',body)
 def test_unclosed_fence(self):
  with self.assertRaises(B.BuildError):B.render('```\nunfinished\n','README.md',REV)
if __name__=='__main__':unittest.main()
