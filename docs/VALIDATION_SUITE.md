# Milestone 2.5 — Multi-Workload Timing Validation

The smoke workload was used to calibrate the current analytical timing rules. This suite freezes those rules and tests them on new workloads before cache/AXI modeling begins.

## Frozen model predictions

| Test | Purpose | Retired | Model cycles | Timing mode |
|---|---|---:|---:|---|
| `smoke` | calibration regression | 10 | 17 | validate |
| `no_hazards` | ideal 5-stage pipeline | 10 | 14 | validate |
| `load_hazards` | three independent load-use interlocks | 11 | 18 | validate |
| `branches` | one not-taken + three taken branches | 11 | 21 | validate |
| `divider` | DIV/DIVU/REM/REMU behavior | 9 | 13 before calibration | measure only |

The first four timing predictions are frozen. The scripts do not modify the model based on VCS output. `divider` is intentionally a measurement test because the divider timing model is still zero-penalty.

## Windows flow

1. Run model-only predictions:

   `python scripts/run_validation_suite.py --model-only`

2. Transfer `RV32IM_VCS_Validation_Suite.zip` to the VCS VM and run the VM flow.
3. Bring `RV32IM_VCS_Validation_Results.zip` back and extract it at this project root. It should populate `results/validation/rtl_*.csv`.
4. Run the final comparison:

   `python scripts/run_validation_suite.py --require-rtl`

The final table reports architectural status, timing status, model cycles, RTL cycles, and cycle error for every workload.
