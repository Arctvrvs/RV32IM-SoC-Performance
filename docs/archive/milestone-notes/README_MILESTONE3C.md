# Milestone 3C - Branch / Wrong-Path I-cache Characterization

Milestone 3B established exact correlation for the pipeline, divider, D-cache, and straight-line IF-stage/I-cache behavior.
Milestone 3C characterizes control-flow redirects before modifying the IFetchStreamModel.

Cases:
- `branch_not_taken`: sequential control case; remains a validation target.
- `branch_taken_forward`: taken forward BEQ; measure wrong-path fetches before EX redirect.
- `branch_backward_loop`: repeated backward BNE into resident cache lines.
- `branch_conflict_loop`: five-instruction loop on a four-line direct-mapped I-cache, forcing refetch/conflict behavior.

Windows first:
```
python scripts/run_milestone3c.py --model-only
```

After VCS results are returned/extracted:
```
python scripts/run_milestone3c.py --require-rtl
python scripts/analyze_branch_fetch.py
```

Taken-branch cases are intentionally `MEASURE` until the exact redirect request stream has been characterized.
