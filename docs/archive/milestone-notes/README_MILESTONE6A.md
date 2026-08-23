# Milestone 6A — Design-Space Exploration

Milestone 6A uses the fully RTL-calibrated RV32IM performance model to explore architectural tradeoffs rather than simply fitting more directed tests.

Run:

```bash
python scripts/run_milestone6a.py
```

Outputs:

- `results/milestone6/design_space.csv`
- `results/milestone6/cache_pareto_frontier.csv`
- `results/milestone6/design_space_report.txt`
- `reference/milestone6b/selected_model_predictions.csv`

The cache cost metric is intentionally a simple **data-array byte proxy** (`4 bytes × total cache lines`). It does not claim physical area, timing, or energy because tag/state arrays and implementation overhead are not modeled.

Milestone 6B freezes four harder validation points that change backing-memory latency, including mixed cache-capacity + latency configurations. Predictions are generated before RTL is run.
