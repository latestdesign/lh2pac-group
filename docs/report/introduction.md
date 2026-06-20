# Introduction

L'objectif de ce projet est d'étudier la conception globale d'un avion, en comparant l'usage de kérosène (UC1) et d'hydrogène liquide (UC2) comme carburants. Cela ce traduit par un problème de minimisation de la masse maximale au décollage (MTOM), sous contraintes. Trois déclinaisons du problème
sont traitées avec la librairie python GEMSEO. La Partie 1 construit un surrogate déterministe
`f_hat(x)` et optimise la conception, en validant systématiquement chaque optimum
sur le vrai modèle couplé. La Partie 2 fige la conception et propage les
incertitudes technologiques `u` pour quantifier la dispersion des sorties et
hiérarchiser les sources d'incertitude (indices de Sobol). La Partie 3 construit
un surrogate conjoint `f_hat(x, u)` et mène une optimisation robuste minimisant
`E[mtom]` sous contraintes de marge. Les résultats montrent qu'un optimum
déterministe sature les contraintes et devient peu fiable sous incertitudes, alors
que la conception robuste rétablit la fiabilité pour un surcoût de masse modeste.

---

## Contexte et objectifs

La conception globale d'avion (Overall Aircraft Design, OAD) est un processus
multidisciplinaire couplant aérodynamique, propulsion, masses, mission et
performances au décollage et à l'approche. On cherche les paramètres de conception
qui minimisent la masse maximale au décollage (MTOM), bon indicateur global du
coût d'un appareil, tout en respectant des exigences opérationnelles strictes.

On note $f : x, u \mapsto f(x, u)$ les sorties d'intérêt du modèle, où $x$ désigne
les **paramètres de conception** et $u$ les **paramètres incertains**
(technologiques). L'évaluation de $f$ étant supposée très coûteuse, on lui
substitue un **modèle surrogate** $\hat{f}$ pour mener les optimisations et les
analyses d'incertitude.

Le problème se décline en trois volets, traités chacun pour les deux cas d'usage :

- **Problème 1 — Optimisation déterministe.** On construit
  $\hat{f} : x \mapsto \hat{f}(x) = f(x, u_{\text{fixe}})$, incertitudes gelées à
  leur valeur nominale, puis on minimise la MTOM sous contraintes.
- **Problème 2 — Quantification des incertitudes.** On fige la conception et on
  construit $\hat{f} : u \mapsto \hat{f}(u) = f(x_{\text{fixe}}, u)$ pour propager
  l'incertitude technologique et l'expliquer (analyse de sensibilité).
- **Problème 3 — Optimisation robuste.** On construit
  $\hat{f} : x, u \mapsto \hat{f}(x, u) = f(x, u)$ sur l'espace conjoint, puis on
  recherche la meilleure conception en tenant compte des incertitudes.

## Cadre commun

| | Description |
|:---|:---|
| **Paramètres de conception $x$** | poussée `slst` (100-200 kN), passagers `n_pax` (120-180), surface alaire `area` (100-200 m$^{2}$), allongement `ar` (5-20) |
| **Contraintes** | `tofl` $\leq$ 1900 m, `vapp` $\leq$ 135 kt, `vz` $\geq$ 300 ft/min, `span` $\leq$ 40 m, `length` $\leq$ 45 m, `fm` $\geq$ 0 % |
| **Objectif** | minimiser la MTOM (`mtom`) |
| **Cas d'usage** | UC1 : kérosène / turbofan $\cdot$ UC2 : hydrogène liquide / turbofan (5500 km) |

Les deux cas d'usage (UC1 et UC2) partagent le même processus multidisciplinaire,
qui couple 11 disciplines, les modèles physiques de `gemseo-oad-training`
(géométrie, aérodynamique, moteur, masses, mission, décollage…), hormis le modèle
de coût `operating_cost`, sans objet ici puisque l'on minimise la `mtom`. La masse
maximale au décollage n'est pas calculée directement : elle est solution d'une
boucle de rétroaction entre les disciplines `mass`, `total_mass` et `mission` (la
masse totale dépend du carburant de mission, qui dépend lui-même de la masse),
résolue par une analyse multidisciplinaire (MDA) à chaque évaluation. Le passage à
l'hydrogène liquide introduit un réservoir cryogénique volumineux qui alourdit et
agrandit le fuselage, modifiant fortement le compromis de conception et ajoutant
deux verrous technologiques incertains (indices gravimétrique `gi` et volumétrique
`vi` du réservoir).


Tous les calculs s'appuient sur la bibliothèque GEMSEO et ses extensions
(`gemseo-oad-training`, `gemseo-umdo`, `gemseo-mlearning`). Le code correspondant
est disponible dans la section **Scripts**.
