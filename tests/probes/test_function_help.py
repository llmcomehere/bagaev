"""Sole help is discovery without input/output; no application execution."""
from pathlib import Path
import contextlib, io, json, os, sys, unittest
from unittest.mock import patch
T=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tools'))
import record_function as cli

class FunctionHelp(unittest.TestCase):
    def call(self,args):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            code=cli.main(args)
        return code,out.getvalue(),err.getvalue()

    def test_aliases_and_no_transport(self):
        with patch.object(cli.transport,'read_input',side_effect=AssertionError('read')), \
             patch.object(cli.transport,'write_output',side_effect=AssertionError('write')):
            first=self.call(['--help']);second=self.call(['-h'])
        self.assertEqual(first,second);self.assertEqual(first[0],0);self.assertEqual(first[2],'')
        text=first[1];self.assertTrue(text.startswith('usage: record_function.py '))
        self.assertLess(len(text.encode()),4096)
        for flag in ('--form','--name','--replacement','--base','--function-pin','--output',
                     '--source-body','--locations','--compact','--callee-context'):
            self.assertIn(flag,text)
        for phrase in ('Default form: 4.','new file','not applied source','No semantic check or execution admission',
                       '--compact requires context --form 5 --source-body and excludes --locations.'):
            self.assertIn(phrase,text)

    def test_environment_and_argv_label(self):
        with patch.dict(os.environ,{'COLUMNS':'20'}),patch.object(sys,'argv',['/private/host/tool.py','--help']):
            short=self.call(None)
        with patch.dict(os.environ,{'COLUMNS':'180'}),patch.object(sys,'argv',['other-name.py','--help']):
            wide=self.call(None)
        self.assertEqual(short,wide);self.assertNotIn('/private/',short[1]);self.assertNotIn('other-name',short[1])

    def test_nonsole_help_keeps_usage_refusal(self):
        with patch.object(cli.transport,'read_input',side_effect=AssertionError('read')), \
             patch.object(cli.transport,'write_output',side_effect=AssertionError('write')):
            for args in ([],['--unknown'],['context','--help'],['--help','context'],['-h','extra']):
                code,out,err=self.call(args)
                self.assertEqual(code,2);self.assertEqual(err,'')
                self.assertEqual(json.loads(out),{'schema':'bagaev-record-function-tool/1','ok':False,
                                                  'error':{'code':'TOOL_USAGE'}})

if __name__=='__main__':unittest.main()
