"""Explicit checked CPython data-artifact CLI; never executes generated code."""
import argparse,os,sys
HELP='''Compile authored form5/profile11 source to a deterministic CPython artifact.
Usage: python -B -S tools/record_cpython_compile.py SOURCE --source-sha256 SHA256 --checker PATH --checker-sha256 SHA256 --output NEW_DIRECTORY
Requires a fresh Python process with -B -S and assertions enabled.
Compilation invokes the explicit pinned checker; generated Python is not executed.
Pins and retained receipts do not grant execution authority.
'''
class Usage(ValueError):pass
class Parser(argparse.ArgumentParser):
    def error(self,message):raise Usage()
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv in (['--help'],['-h']):
        try:print(HELP,end='',flush=True)
        except OSError:return 1
        return 0
    try:
        p=Parser(add_help=False,allow_abbrev=False)
        p.add_argument('source');p.add_argument('--source-sha256',required=True)
        p.add_argument('--checker',required=True);p.add_argument('--checker-sha256',required=True)
        p.add_argument('--output',required=True);a=p.parse_args(argv)
    except Usage:
        print('CPY_USAGE',file=sys.stderr);return 2
    try:
        import record_source_cpython as compiler
        _,receipt=compiler.compile_flow(a.source,a.checker,a.source_sha256,a.checker_sha256,a.output)
        try:sys.stdout.buffer.write(compiler.canonical(receipt)+b'\n');sys.stdout.buffer.flush()
        except OSError:
            # Avoid a second buffered stdout failure at interpreter shutdown.
            fd=os.open(os.devnull,os.O_WRONLY)
            try:os.dup2(fd,sys.stdout.fileno())
            finally:os.close(fd)
            print('CPY_DELIVERY',file=sys.stderr);return 1
        return 0
    except ValueError as error:
        # Import-time fresh-load refusals use the same exact CompileError type.
        if type(error).__name__!='CompileError' or not hasattr(error,'code'):raise
        print(error.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
