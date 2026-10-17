# Inspect an L2/2 change before running it

Use the existing workflow CLI for structural inspection. The smaller
`src.bagaev_filter` CLI handles prepare/check/run/compile/patch; it does not
provide inspect or diff. These commands neither run the program nor open a Store:

```sh
python3 -B -m src.bagaev_filter_workflow inspect examples/l2-filter/queue.json
python3 -B -m src.bagaev_filter_workflow diff examples/l2-filter/queue.json examples/l2-filter/store/queue-refactor.json
```

Run from the repository root. Both commands print JSON to stdout and do not
create an output file. They validate the versioned program and its definition
pins first. For these existing fixtures:

- The original source identity is
  `sha256:d08da50bd3d9b80eead8f2b018c7961696c037e1840dfd90701d8588be83d4fa`.
- The refactored identity is
  `sha256:a1bd8fdf7c23e8cf9d1329a15c5862d82a7db114dd8fe6b9948875189bdb2018`.
- Inspect lists `identifier`, `job-valid`, `key`, `main`, `valid` in order.
  Their direct dependencies are respectively none, `identifier`, none,
  `key` plus `valid`, and `job-valid`.
- Diff reports `entry_changed: false`, no added or removed definitions,
  and `main` as the only changed definition and changed pin. The refactor
  introduces a local `retainedResult` binding in that definition.

Inspect reports each definition's pin and parameter names; diff reports both
source identities. Comparing a source with itself returns empty change lists.
Wrong language versions or malformed input refuse with `ok: false` and exit2.
L2/1 documents must use their own route, not an implicit conversion.

These structural facts do not prove that all outputs agree, grant execution
admission, or accept a saved revision. Running, patch publication, Store
admission and restore retain their separate contracts. A successful inspection
does not open or initialize the directory named `store` in this example; that
directory merely contains the existing refactored input fixture.
