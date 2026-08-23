# RV32IM Milestone 3C — Calibrated Redirect-Aware I-Cache Model

This package updates the analytical IF-stage model using the VCS branch-fetch characterization.

## Calibrated rule

For a taken conditional branch in the current 5-stage RTL:

1. The branch resolves in EX.
2. IF has already issued the two younger sequential requests at `branch_pc+4` and `branch_pc+8`.
3. Those wrong-path requests access the real direct-mapped I-cache and can miss.
4. IF then restarts at the architectural branch target.
5. A backward target is a new cache request even if that PC was fetched previously.

The existing two-cycle branch redirect penalty remains separate from I-cache stall cycles.

## Measured VCS targets

| workload | cycles | I$ accesses | I$ hits | I$ misses |
|---|---:|---:|---:|---:|
| branch_not_taken | 66 | 10 | 2 | 8 |
| branch_taken_forward | 74 | 11 | 2 | 9 |
| branch_backward_loop | 74 | 18 | 10 | 8 |
| branch_conflict_loop | 188 | 27 | 4 | 23 |

For `branch_conflict_loop`, the old retired-PC approximation predicted 104 cycles and 11 misses. Replaying the actual redirect stream naturally creates 12 more direct-mapped misses. At a 7-cycle clean-refill penalty, that is 84 additional cycles, producing the measured 188 cycles without an aggregate correction constant.

## Windows validation

Keep the real VCS result files already generated under `results/milestone3c/`, then run:

```bash
python scripts/run_milestone3c.py --require-rtl
python scripts/analyze_branch_fetch.py
```

Expected: all four branch cases PASS architecture, timing, and I-cache statistics.

## Regression

The change is isolated to taken conditional redirects. Milestone 2 pipeline/divider predictions and Milestone 3B straight-line/I-D-cache predictions remain unchanged.

## Next

Before using Dhrystone for full-model correlation, characterize JAL and JALR redirects because function calls/returns are common in real code and may have different front-end redirect timing from conditional branches.
