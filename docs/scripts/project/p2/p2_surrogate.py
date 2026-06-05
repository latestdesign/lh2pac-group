"""Problem 2 — Surrogate ``f̂(u)`` at a fixed design (for uncertainty studies).

Skeleton to be completed by the Problem-2 contributor. Problem 2 freezes the
design ``x`` and studies the effect of the technological uncertainties ``u``: build
a surrogate of the objective and constraints with respect to ``u`` alone,
``f̂(u) = f(x_fixed, u)`` (at the initial design and/or the Problem-1 optimum),
validate it, and cache it for the sensitivity and UQ steps — for both use cases
(UC1, UC2).
"""
