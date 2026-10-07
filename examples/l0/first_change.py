"""Run the existing L0 change end to end; read fixed fixtures, write no files."""
from pathlib import Path
import copy
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import bagaev_l0 as l0


def demonstrate():
    directory = ROOT / "examples" / "l0"
    program = l0.load_json_file(directory / "tag_list.json")
    patch = l0.load_json_file(directory / "tag_unique_sorted.patch")
    inputs = l0.load_json_file(directory / "tag_inputs.json")
    original = copy.deepcopy((program, patch, inputs))
    before = l0.run_program(program, inputs)
    candidate = l0.apply_patch(program, patch)
    after = l0.run_program(candidate, inputs)
    try:
        l0.apply_patch(candidate, patch)
    except l0.L0Error as error:
        if error.code != "patch.stale":
            raise
        replay = error.code
    else:
        raise RuntimeError("The old-base patch unexpectedly applied twice")
    if (program, patch, inputs) != original:
        raise RuntimeError("The demonstration mutated its inputs")
    return {"before": before, "after": after, "old_base_retry": replay}


if __name__ == "__main__":
    print(json.dumps(demonstrate(), sort_keys=True, separators=(",", ":")))
