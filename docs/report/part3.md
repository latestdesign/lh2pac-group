# Part 3 — Surrogate modeling and robust optimization

**Goal.** Build a surrogate `f̂(x, u) = f(x, u)` over **both** the design and the
uncertain parameters, then perform a **robust optimization**: minimise the
*expected* maximum take-off mass `E[mtom]` while enforcing each constraint with a
safety margin `mean ± kσ` (here `k = 2`). This is a **moment-based robustness
proxy**, not a probabilistic guarantee: with non-Gaussian (triangular, nonlinear)
outputs the `k = 2` band does *not* certify a 97.7 % reliability — the actual
reliabilities are **measured by Monte-Carlo** below rather than assumed.

**Method.** A joint Latin-Hypercube design (10 × dimension) trains the surrogate;
Linear, RBF and **Kriging** (Gaussian process) are compared on a test set. The
robust scenario (`gemseo-umdo`, `UMDOScenario`) minimises the `Mean` of MTOM,
estimated by an inner Monte-Carlo, under the margin constraints. Crucially, the
surrogate is only used to *search*: both optima are then **verified on the true
coupled model** — the reported MTOM and reliabilities are read off `f`, not `f̂`,
by propagating the uncertainties through the true model at each design.

---

## Use Case 1 — Kerosene / Turbofan

> _Section to be completed._

---

## Use Case 2 — Liquid H₂ / Turbofan

### Joint DoE and surrogate validation

The OAD model is a genuine multidisciplinary system: the disciplines are tied by
a feedback loop on the take-off mass, resolved by a multidisciplinary analysis
(MDA) at **every** DoE sample. The condensed coupling graph makes this explicit —
`mass`, `total_mass` and `mission` (plus the silent `battery`) form the
strongly-coupled core, fed by `geometry`, `aerodynamic` and `engine`, and feeding
the take-off, approach and climb constraints.

![UC2 P3 discipline coupling graph](../images/use_case/uc2_p3_coupling.png)

![UC2 P3 joint DoE vs MTOM](../images/use_case/uc2_p3_doe.png)
![UC2 P3 surrogate validation](../images/use_case/uc2_p3_validation.png)

In the 9-dimensional joint space we keep the **Kriging** (Gaussian-process) model.
Linear, RBF and Kriging all reach a high global R² for MTOM (≈ 0.98–0.99), but
the optimum sits in a *corner* of the joint space (`slst` and `n_pax` on their
lower bounds) where a space-filling DoE is sparse and the RBF reverts toward the
training mean — over-predicting MTOM there by ~2 %. The Gaussian process is far
better calibrated on the **constraints** in that region (test R² for `vapp`,
`vz`, `tofl`, `span` all ≥ 0.997 vs ≈ 0.96–0.99 for RBF), which is what lets the
optimizer locate the right design. A K-fold **cross-validation** confirms no
over-fitting (CV R² = 0.991 for MTOM, ≥ 0.98 for every output); the grey hatched
bars show it tracking the single-split test R². The DoE and all Monte-Carlo steps
are seeded, so the figures are reproducible.

Even so, a surrogate is only an approximation: at the optimum the Gaussian process
still over-predicts MTOM by ~0.5 % (≈ 300 kg). We therefore **verify the optimum
on the true model**, and report those values below.

### Robust optimization

![UC2 P3 robust optimization convergence](../images/use_case/uc2_p3_robust_history.png)

Here robustness is essential. The robust optimum
(`slst = 100 kN`, `n_pax = 120`, `area = 117.9 m²`, `ar = 9.53`) has a true
nominal MTOM of **≈ 63 650 kg (~63.6 t)**. Propagating the same uncertainties
through the **true** model at each design, its expected MTOM is **64 329 kg**
against **64 202 kg** for the deterministic design — a **price of robustness of
only +127 kg (+0.2 %)**. (`slst` and `n_pax` sit on their lower bounds for *both*
designs: the optimizer wants minimum thrust and the fewest passengers to cut
mass, so those two variables are set by the design-space floor, not the
constraints.)

![UC2 P3 constraint reliability: deterministic vs robust](../images/use_case/uc2_p3_feasibility.png)

This is the key figure of Part 3, and it is computed on the **true model**. The
deterministic (nominally optimal) design is **probabilistically fragile**: under
the technological uncertainties it satisfies the **climb-rate** constraint `vz`
only **11.8 %** of the time, the **fuel margin** `fm` **46.4 %**, and the take-off
field length `tofl` **88.2 %** — it is optimal at the nominal point but sits right
on those constraint boundaries, so any adverse `gi`/`vi`/`cef` draw violates them.
The robust design lifts all constraints to **≥ 98 %** (`vz` 99.7 %, `fm` 98.5 %,
`tofl` 98.2 %, `vapp` 100 %) by **enlarging the wing and raising its aspect ratio**
(area 117.9 vs 115.5 m², `ar` 9.53 vs 8.82), which improves the lift-to-drag
ratio — cutting mission fuel to restore margin — for the very modest mass cost
above. The robust hydrogen design is therefore strongly preferable to the
deterministic one.

![UC2 P3 deterministic vs robust aircraft](../images/use_case/uc2_p3_robust_vs_det.png)
