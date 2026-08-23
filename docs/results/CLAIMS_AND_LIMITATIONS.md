# Claims and Limitations

## Defensible claims

- Exact directed RTL timing correlation for the tested microarchitectural rules.
- Exact full-Dhrystone architectural cycle/retirement/signature correlation.
- Exact cache miss/writeback counts for the validated configurations.
- Exact synchronous-SRAM architectural cycle results.
- Explicit RAM2P_128x16 macro counts.
- Genus pre-layout standard-cell implementation estimates.
- SAIF-driven pre-layout power/energy estimates.
- Innovus hard-macro import and non-timing-driven floorplan/placement area.
- Equal-clock cycle-performance per physical core area.

## Does not claim

- Silicon Fmax.
- SRAM-aware post-layout Fmax.
- Wall-clock SRAM-backed speedup.
- Routed/signoff PPA.
- Antenna-clean signoff.
- Signoff RC extraction.
- SRAM timing derived from patched or mismatched Liberty data.

## Reason

The physically matched RAM2P_128x16 timing model has placeholder 999-ns
clock-to-Q tables, and the available Innovus RC setup also lacks the collateral
needed for a signoff timing claim.
