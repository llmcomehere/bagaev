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
   a={f.relative_to(p/'one').as_posix():f.read_bytes() for f in (p/'one').rglob('*') if f.is_file()};b={f.relative_to(p/'two').as_posix():f.read_bytes() for f in (p/'two').rglob('*') if f.is_file()};self.assertEqual(a,b);self.assertEqual(len(a),len(B.SOURCES)+2)
   m=json.loads(a['index.json']);self.assertEqual(len(m['sources']),len(B.SOURCES))
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
  for name in ('component-text-cli', 'component-arithmetic-form', 'component-arithmetic-edits', 'component-diagnostics', 'readable-authoring', 'component-match-form', 'component-match-edits', 'stock-adjustment', 'component-expression-locations', 'component-text-list-form', 'tag-box', 'component-fold-form', 'tag-box-budget', 'component-record-list-form', 'pure-record-form', 'pure-reindex-entry', 'pure-batch-reindex', 'record-diagnostics'):
   self.assertEqual(B.link(name+'.md','docs/readable-authoring.md',REV),name+'.html')
 def test_documented_counts_match_selection(self):
  text=(P/'docs/offline-documentation.md').read_text()
  n=len(B.SOURCES)
  self.assertIn(f'contains {n} reviewed documentation sources',text)
  self.assertIn(f'{n} sources produce {n+1} HTML pages',text)
  self.assertIn(f'index.json: {n+2} files in total',text)
 def test_current_pure_routes(self):
  self.assertEqual(len(B.SOURCES),76);self.assertEqual(len(set(B.SOURCES)),76)
  for name in ('pure-record-drafts', 'pure-change-workflow', 'pure-option-form', 'pure-optional-fields', 'pure-json-form', 'catalog-edit-workflow', 'focused-function-edits', 'function-context', 'record-formatting', 'record-wide-profile', 'catalog-wide', 'wide-function-editing', 'wide-authoring', 'record-draft-export', 'record-capabilities', 'pure-inventory-reservation', 'inventory-focused-change', 'offline-documentation', 'application'):
   self.assertEqual(B.link(name+'.md','docs/choose-and-start.md',REV),name+'.html')
 def test_current_json_native_routes(self):
  for name in ('probe-native-wide-emitter', 'probe-native-wide-wire', 'probe-native-wide-adapter', 'probe-native-wide-qualification', 'probe-native-wide-followthrough', 'inventory-json', 'json-argument-prepare', 'inventory-json-focused-change', 'native-source-locations', 'record-source-map', 'inventory-batch', 'inventory-batch-change', 'inventory-native-baseline', 'prepared-json11-reference', 'prepared-json11-native', 'native-result-json11'):
   self.assertEqual(B.link(name+'.md','docs/choose-and-start.md',REV),name+'.html')
 def test_inert_code_and_raw_html(self):
  code='<script>alert("x")</script> & [link](javascript:x)\n';body,title=B.render('# Example\n\n```text\n'+code+'```\n\n<img src=x onerror=alert(1)>\n','README.md',REV);parser=Tags();parser.feed(body);self.assertNotIn('script',parser.tags);self.assertNotIn('img',parser.tags);self.assertEqual(''.join(parser.code),code)
 def test_form6_routes_and_fixture_boundary(self):
  names=('record-json-bool-proposal','json-bool-authoring','form6-callee-context','form6-authored-layout','json-active-total','json-active-authoring','probe-prepared-json12','native-result-json12','native-source-locations12')
  for name in names:
   self.assertEqual(B.link(name+'.md','docs/choose-and-start.md',REV),name+'.html')
  for path in ('examples/probes/json-active-authoring/pins.json','tests/probes/test_json_active_authoring.py'):
   self.assertNotIn(path,B.SOURCES)
   self.assertEqual(B.link('../'+path,'docs/json-active-authoring.md',REV),B.REPOSITORY+'/blob/'+REV+'/'+path)
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
 def test_inline_inside_bold(self):
  cases=(
   ('**Read the [compact language reference](docs/choose-and-start.md).**','<strong>Read the <a href="docs/choose-and-start.html">compact language reference</a>.</strong>'),
   ('**Use `x < y` and [guide](docs/choose-and-start.md#types).**','<strong>Use <code>x &lt; y</code> and <a href="docs/choose-and-start.html#types">guide</a>.</strong>'),
   ('**[<img src=x>](https://example.com?q=1&x=2)**','<strong><a href="https://example.com?q=1&amp;x=2">&lt;img src=x&gt;</a></strong>'),
   ('**`[x](javascript:alert)`**','<strong><code>[x](javascript:alert)</code></strong>'),
   ('`**[x](javascript:alert)**`','<code>**[x](javascript:alert)**</code>'),
   ('**plain <text> & value**','<strong>plain &lt;text&gt; &amp; value</strong>'))
  for source,expected in cases:
   with self.subTest(source=source):self.assertEqual(B.inline(source,'README.md',REV),expected)
 def test_unsafe_links_inside_bold_refuse_before_output(self):
  for target in ('javascript:alert','data:text/plain,x','file:///tmp/x','//example.com','../private','%2e%2e/private'):
   with self.subTest(target=target),tempfile.TemporaryDirectory() as d:
    p=Path(d);root=p/'source';self.fixture(root,'# Example\n\n**[x]('+target+')**\n');out=p/'output'
    with self.assertRaises(B.BuildError):B.build(root,out,REV)
    self.assertFalse(out.exists())
 def test_primary_readme_link_is_an_anchor(self):
  body,_=B.render((P/'README.md').read_text(),'README.md',REV)
  self.assertIn('<strong>Read the <a href="docs/choose-and-start.html">compact language reference</a>.</strong>',body)
  self.assertLessEqual((P/'README.md').stat().st_size,4096)
 def test_complete_record_list_formula(self):
  source=(P/'docs/choose-and-start.md').read_text()
  self.assertLessEqual(len(source.encode('utf-8')),32768)
  body,_=B.render(source,'docs/choose-and-start.md',REV)
  self.assertIn('<code>record-list=1+capacity*element_units</code>',body)
  self.assertNotIn('<li>element units.',body)
if __name__=='__main__':unittest.main()
