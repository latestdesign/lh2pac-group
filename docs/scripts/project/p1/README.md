# Problème 1 — Optimisation déterministe (MDO)

Scripts du Problème 1 (optimisation déterministe : incertitudes technologiques
gelées à leurs valeurs nominales, seuls les 4 paramètres de conception
x = (slst, n_pax, area, ar) varient) pour les deux cas d'usage (UC1 kérosène,
UC2 hydrogène liquide) : plan d'expériences sur le vrai modèle couplé
(`p1_doe`), études justificatives du couple métamodèle/taille de plan
(`p1_model_study`) et de l'algorithme d'optimisation COBYLA vs SLSQP
(`p1_algo_study`), entraînement et validation du surrogate déterministe
f_hat(x) (`p1_surrogate`), puis minimisation du MTOM sur ce surrogate avec
vérification de l'optimum sur le vrai modèle (`p1_optimization`). L'optimum
déterministe sert de référence au Problème 3. Les jeux de données et surrogates
générés sont stockés dans `data/`.
