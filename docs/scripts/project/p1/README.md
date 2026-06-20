# Problème 1 — Optimisation déterministe (MDO)

Optimisation déterministe (incertitudes gelées au nominal, seuls les 4 paramètres
de conception x = (slst, n_pax, area, ar) varient), pour les deux cas d'usage
(UC1 kérosène, UC2 hydrogène liquide) :

- `p1_doe` : plan d'expériences sur le vrai modèle couplé;
- `p1_model_study` : choix du couple métamodèle / taille de plan;
- `p1_algo_study` : choix de l'algorithme d'optimisation (COBYLA vs SLSQP);
- `p1_surrogate` : entraînement et validation du surrogate déterministe f_hat(x);
- `p1_optimization` : minimisation du MTOM sur le surrogate, optimum vérifié sur
  le vrai modèle (référence du Problème 3).

Jeux de données et surrogates stockés dans `data/`.
