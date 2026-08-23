# Milestone 4B — overlap-aware full-workload calibration

This milestone closes the Dhrystone-scale correlation gaps using VCS-characterized concurrency semantics, not benchmark address constants.

## Rules

- If an older **store D$ miss** is active while the immediately younger EX-stage branch/JAL/JALR redirects to an **I$-missing target**, the I$ refill overlaps the tail of the D$ wait. Overlap credit is `min(I$ clean refill, D$ stall - 1)`.
- If D$ responds underneath that IF miss, `dmem_valid` gating causes one filled-line D$ replay after IF releases. It is a hit and creates no new AXI transaction or stall.
- Effective load-use/divider holds cause IF hit replays. These change I$ access/hit counters, not miss latency. Cache-overlap cycles suppress duplicate replay accounting.

Canonical fresh VCS target: 193,203 retired; 1,365,926 cycles; I$ 368,993/226,574/142,419; D$ 79,394/68,740/10,654 with 6,056 writebacks.

```bash
python scripts/run_milestone4.py --model-only
python scripts/run_milestone4.py --require-rtl
```

## Next: Milestone 5A sensitivity predictions

After exact correlation, run:

```bash
python scripts/run_sensitivity_sweep.py
```

This sweeps I$ capacity, D$ capacity, memory latency, and selected combined cache configurations. Results are explicitly labeled **model predictions** until selected candidates are validated in VCS.

## Milestone 5A first findings

The frozen Dhrystone sensitivity sweep predicts:

- I$128 / D$64: **1,236,398 cycles** (9.483% reduction)
- I$256 / D$64: **715,815 cycles** (47.595% reduction)
- I$512 / D$64: **373,403 cycles** (72.663% reduction)
- I$256 / D$256: **638,963 cycles** (53.221% reduction)

These are predictions, not validated claims. Use the separate Milestone 5B VCS bundle to test those four points. After extracting its result ZIP back into this project, run:

```bash
python scripts/compare_milestone5b.py
```
