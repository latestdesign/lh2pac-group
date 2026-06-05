# Part 3 — Surrogate modeling and robust optimization

**Goal.** Build a surrogate `f̂(x, u) = f(x, u)` over **both** the design and the
uncertain parameters, then perform a **robust optimization**: minimise the
*expected* maximum take-off mass `E[mtom]` while enforcing each constraint with a
safety margin `mean ± kσ` (here `k = 2`), so that it stays satisfied despite the
technological uncertainties.

**Method.** A joint Latin-Hypercube design (5 × dimension) trains the surrogate;
Linear and RBF are compared on a test set. The robust scenario
(`gemseo-umdo`, `UMDOScenario`) minimises the `Mean` of MTOM, estimated by an
inner Monte-Carlo, under the margin constraints. The robust optimum is then
compared to the Part-1 deterministic optimum by propagating the uncertainties
through the surrogate at each design.

---

## Use Case 1 — Kerosene / Turbofan

> _Section to be completed._

---

## Use Case 2 — Liquid H₂ / Turbofan

### Joint DoE and surrogate validation

![UC2 P3 joint DoE vs MTOM](figs/uc2_p3_doe.png)
![UC2 P3 surrogate validation](figs/uc2_p3_validation.png)

In the 9-dimensional joint space **RBF** is again selected (test R² = 0.989 for
MTOM). The tank parameters `gi`/`vi` contribute visibly to the scatter, as
anticipated by the Part-2 sensitivities.

### Robust optimization

![UC2 P3 robust optimization convergence](figs/uc2_p3_robust_history.png)

Here robustness is essential. The robust optimum
(`slst = 100 kN`, `n_pax = 120`, `area = 119 m²`, `ar = 9.5`) has an expected
MTOM of **65 602 kg** against **65 468 kg** for the deterministic design — a
**price of robustness of only +134 kg (+0.2 %)**.

![UC2 P3 constraint reliability: deterministic vs robust](figs/uc2_p3_feasibility.png)

This is the key figure of Part 3. The deterministic design satisfies the
**approach-speed** constraint only **11.3 %** of the time; the robust design
raises this to **97.0 %** (and keeps `vz`, `fm` ≥ 99 %). It does so by
**enlarging the wing** (area 119 vs 113 m², lower aspect ratio) to gain
approach-speed margin, at the very modest mass cost above. The robust hydrogen
design is therefore strongly preferable to the deterministic one.

![UC2 P3 deterministic vs robust aircraft](figs/uc2_p3_robust_vs_det.png)
