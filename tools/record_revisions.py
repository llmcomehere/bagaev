#!/usr/bin/env python3
"""Portable source history CLI; no evaluation, admission or mutable head."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import bagaev_record_revisions as legacy
import record_text as transport


def main(argv=None):
    try:
        parser = transport.Parser(add_help=False, allow_abbrev=False)
        parser.add_argument('operation', choices=('init', 'append', 'inspect', 'checkout'))
        parser.add_argument('input')
        parser.add_argument('--form', choices=('5', '6'), default='5')
        parser.add_argument('--output', required=True)
        parser.add_argument('--source')
        parser.add_argument('--source-sha256')
        parser.add_argument('--program-sha256')
        parser.add_argument('--package-sha256')
        parser.add_argument('--head')
        parser.add_argument('--revision')
        args = parser.parse_args(argv)
        if args.form == '6':
            import bagaev_record_revisions_form6 as revisions
        else:
            revisions = legacy
        selected = {name for name in ('source', 'source_sha256', 'program_sha256',
                    'package_sha256', 'head', 'revision') if getattr(args, name) is not None}
        expected = {
            'init': {'source_sha256', 'program_sha256'},
            'append': {'source', 'source_sha256', 'program_sha256', 'package_sha256', 'head'},
            'inspect': set(), 'checkout': {'revision'}}[args.operation]
        if selected != expected:
            raise transport.Refusal('TOOL_USAGE')
        raw = transport.read_input(args.input)
        if args.operation == 'init':
            output = revisions.canonical(revisions.initialize(raw,
                source_sha256=args.source_sha256, program_sha256=args.program_sha256))
        else:
            package = revisions.loads(raw)
            if args.operation == 'append':
                output = revisions.canonical(revisions.append(package,
                    transport.read_input(args.source), expected_package_sha256=args.package_sha256,
                    expected_head=args.head, source_sha256=args.source_sha256,
                    program_sha256=args.program_sha256))
            elif args.operation == 'inspect':
                output = revisions.canonical(revisions.inspect(package))
            else:
                output = revisions.checkout(package, args.revision)
        transport.write_output(args.output, output)
        return 0
    except (transport.Refusal, legacy.RevisionError) as error:
        print(error.code, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
