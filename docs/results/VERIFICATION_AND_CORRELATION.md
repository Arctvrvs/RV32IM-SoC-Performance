# Verification and Correlation Summary

## Directed cycle tests

Exact RTL/model timing was established with small tests before Dhrystone:

- smoke: 17 cycles
- no_hazards: 14 cycles
- load_hazards: 18 cycles
- branches: 21 cycles
- divider: 20 cycles

Additional directed checks covered cache clean/dirty misses, wrong-path fetch,
JAL/JALR redirects, segment-like control effects in the surrounding test
infrastructure, and overlapping instruction/data stalls.

## Full benchmark invariants

Canonical Dhrystone invariants:

- cycles: 1,365,926
- retired: 193,203
- x5: 0x003fffff
- I$ accesses/hits/misses: 368,993 / 226,574 / 142,419
- D$ accesses/hits/misses: 79,394 / 68,740 / 10,654
- D$ writebacks: 6,056

## Why the correlation is meaningful

The model does not apply an empirical correction factor. It encodes the actual
pipeline/cache protocol rules and reproduces RTL observables, including
load-use/pipe overlap, divider overlap, wrong-path fetches, cache stall
interaction, and branch/jump redirect behavior.
