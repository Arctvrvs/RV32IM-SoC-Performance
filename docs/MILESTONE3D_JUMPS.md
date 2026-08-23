# Milestone 3D — JAL/JALR call-return I-cache characterization

Milestone 3C calibrated conditional-branch redirects. Milestone 3D measures the remaining control-flow redirects needed before a compiled benchmark: direct `JAL`, backward `JAL x0`, register-indirect `JALR`, and a real call/return sequence.

All four cases begin as **MEASURE**. The C++ predictions are frozen before VCS is run; do not tune them first.

Windows model-only:

```bash
python scripts/run_milestone3d.py --model-only
```

After running the VCS bundle and extracting its results at the project root:

```bash
python scripts/run_milestone3d.py --require-rtl
python scripts/analyze_jump_fetch.py
```

The characterization should answer:

- whether JAL/JALR have the same 2-cycle EX redirect penalty as conditional branches;
- how many younger sequential I-cache requests escape before a jump redirect;
- whether backward JAL/JALR restarts the IF request stream like a taken branch;
- whether a JALR return has any distinct fetch behavior from direct JAL.
