"""Discover existing authored-record tools without changing their contracts."""
import importlib
import sys

ROUTES = {
    "diff": ["record_source_diff", []],
    "run-cpython": ["record_cpython_run", []],
    "verify-cpython-run": ["record_cpython_run_verify", []],
    "verify-cpython-run-expectation": ["record_cpython_run_expectation", []],
    "check": [
        "record_source_check",
        []
    ],
    "run": [
        "record_source_run",
        []
    ],
    "inspect": [
        "record_text",
        [
            "inspect",
            "--form",
            "5"
        ]
    ],
    "diagnose": [
        "record_diagnose",
        []
    ],
    "format": [
        "record_format",
        []
    ],
    "source-map": [
        "record_source_map",
        []
    ],
    "function": [
        "record_function",
        []
    ],
    "draft": [
        "record_draft",
        []
    ],
    "export": [
        "record_export",
        []
    ],
    "compile-cpython": [
        "record_cpython_compile",
        []
    ],
    "history": [
        "record_revisions",
        []
    ],
    "history-store": [
        "record_history_store",
        []
    ],
    "verify-run": [
        "record_run_verify",
        []
    ],
    "verify-run-expectation": [
        "record_run_expectation",
        []
    ],
    "verify-expectation-set": [
        "record_expectation_set",
        []
    ],
    "check-location": [
        "record_check_location",
        []
    ],
    "failure-location": [
        "record_failure_location",
        []
    ]
}
HELP = "Bagaev authored-record commands\ncheck                  Pinned source-only semantic check\nrun                    Explicit reference execution; separate authority required\ninspect                Data-only inspection; form5 default, explicit --form 6\ndiff                   Read-only pinned form5 structural comparison, not a patch\nfunction               Extract/context/replace; replacement produces a draft packet\ndraft                  Restricted multi-body draft packet; not applied source\nexport                 Validate and export a draft packet to fresh source\ncompile-cpython        Checked form5/profile11 artifact; no generated execution\nrun-cpython            Fresh checked source run; separately reviewed Python pin required\nverify-cpython-run     Retained CPython consistency; no execution or authentication\nverify-cpython-run-expectation  Compare retained CPython data with pinned expectations\nhistory                Portable form5/form6 revision packages\nhistory-store          Local candidate history storage; not admission\nverify-run             Retained source-run consistency\nverify-run-expectation Compare one retained run with supplied expectations\nverify-expectation-set Compare a complete supplied obligation set\ncheck-location         Bound checker refusal to explicit form5/form6 source\nfailure-location       Bound retained runtime failure to pinned source\nformat                 Token-preserving source formatting\ndiagnose               Source syntax diagnostics\nsource-map             Explicit source/program-bound locations\nPass the remaining arguments unchanged to the documented delegate.\nUse Python -B -S with assertions and an authorized execution profile.\nDrafts, artifacts, hashes and consistency checks grant no execution authority.\n"


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments in (['--help'], ['-h']):
        sys.stdout.write(HELP)
        return 0
    if not arguments or arguments[0] not in ROUTES:
        sys.stderr.write('RECORD_COMMAND\n')
        return 2
    module_name, prefix = ROUTES[arguments[0]]
    # Help and unrelated routes must not preload the compiler's source closure.
    delegate = importlib.import_module(module_name)
    return delegate.main([*prefix, *arguments[1:]])


if __name__ == '__main__':
    raise SystemExit(main())
