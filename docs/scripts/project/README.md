# Projet

Scripts de conception globale d'avion (OAD) comparant kérosène (UC1) et hydrogène
liquide (UC2), organisés par problème :

- `p1/` — optimisation déterministe (surrogate `f_hat(x)`);
- `p2/` — quantification des incertitudes et sensibilité (`f_hat(u)`);
- `p3/` — optimisation robuste sur l'espace conjoint (`f_hat(x, u)`).

`_oad.py` regroupe la définition partagée du problème (disciplines, espaces,
contraintes, sélection de surrogate, helpers de figures), importée par tous les
scripts. Le détail de chaque étape est dans le README de son dossier; l'analyse
des résultats est dans le rapport (`docs/report/`).
