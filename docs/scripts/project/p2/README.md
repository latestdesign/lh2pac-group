# Problème 2 — Quantification des incertitudes et sensibilité

Scripts du Problème 2 (la conception `x` est figée et l'on étudie l'effet des
incertitudes technologiques `u` sur les sorties) pour les deux cas d'usage
(`p2_uc1` kérosène, `p2_uc2` hydrogène liquide) : propagation des incertitudes à
travers le vrai modèle couplé à 11 disciplines, ajustement et validation d'un
surrogate RBF de `f(u)`, propagation Monte-Carlo et analyse de sensibilité par
indices de Sobol sur ce surrogate, puis statistiques empiriques et distribution
de la MTOM sous incertitudes. L'espace incertain dépend du cas d'usage :
`aef`/`cef`/`sef` pour le kérosène, `gi`/`vi`/`aef`/`sef` pour l'hydrogène
liquide. La conception est figée au point optimal X_opt ou initial X_init selon
le bloc activé en tête de script.
