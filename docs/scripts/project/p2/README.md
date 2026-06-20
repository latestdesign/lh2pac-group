# Problème 2 — Quantification des incertitudes et sensibilité

Conception `x` figée, étude de l'effet des incertitudes technologiques `u` sur les
sorties, pour les deux cas d'usage :

- `p2_uc1` (kérosène) : incertitudes `aef`/`cef`/`sef` ;
- `p2_uc2` (hydrogène liquide) : incertitudes `gi`/`vi`/`aef`/`sef`.

Chaque script propage `u` à travers le vrai modèle couplé à 11 disciplines, ajuste
et valide un surrogate RBF de `f(u)`, puis mène propagation Monte-Carlo, indices de
Sobol et statistiques de la MTOM sur ce surrogate. La conception est figée au point
optimal X_opt ou initial X_init selon le bloc activé en tête de script.
