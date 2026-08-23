# RV32IM Milestone 4A - Full-workload Dhrystone correlation

Milestones 2-3D calibrated pipeline, divider, cache, branch, JAL, and JALR behavior on directed tests. Milestone 4A applies those rules unchanged to the original project's Dhrystone benchmark.

## Windows

```bash
python scripts/run_milestone4.py --model-only
```

The current source-derived prediction is expected to be within a few cycles of the original published RTL result while reproducing the benchmark signature and cache miss/writeback counts.

After the fresh VCS result ZIP is extracted at the project root:

```bash
python scripts/run_milestone4.py --require-rtl
python scripts/analyze_milestone4_gaps.py
```

The remaining difference is treated as characterization data. Do not add a benchmark-specific constant.
