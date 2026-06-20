# Conclusion

Ce projet a appliqué la conception globale d'avion (OAD) à un appareil de 150
passagers, en comparant l'utilisation de **kérosène** (UC1) et d'**hydrogène
liquide** (UC2) en tant que carburants à travers trois problèmes complémentaires, tous résolus en
remplaçant le modèle vrai, coûteux, par un surrogate validé.

Les trois problèmes ne sont pas indépendants : ils suivent un **même vecteur de
conception** $x$, qu'ils transforment et éprouvent tour à tour. C'est ce fil qui
relie l'ensemble.

```text
              P1 — MDO déterministe              P3 — MDO robuste
            (min mtom à u nominal)          (min E[mtom] sous marges)
  x0  ─────────────────────────────▶  x*  ─────────────────────────▶  x̃
 conception                        optimum nominal                optimum robuste
 initiale                          ~63 t mais sature              ~64 t, toutes les
 (~75-77 t)                        les contraintes                fiabilités ≥ 98 %
                                          │
                                          ▼
                          P2 — quantification des incertitudes
                          (propagation + indices de Sobol)
                          → x* est probabilistiquement fragile,
                            peut violer les contraintes sous u
```

La **Partie 1** part de la conception initiale $x_0$ (avion lourd, $\approx$ 75-77 t sous
incertitudes) et la transforme en l'optimum déterministe $x^\star$ ($\approx$ 63 t), qui
sature les contraintes. La **Partie 2** fige tour à tour $x_0$ puis $x^\star$ et y
propage les incertitudes : la variance de la masse y est gouvernée par un unique
verrou technologique (la masse structurale `sef` pour le kérosène, l'indice de
réservoir cryogénique `gi` pour l'hydrogène). Pour l'hydrogène, l'optimisation
*accentue* encore ce verrou (`gi` 64 % $\to$ 72 %) et rend $x^\star$, posé sur ses
contraintes, fragile (marge de carburant moyenne négative sous $u$). La **Partie 3** ré-optimise
en intégrant $u$ dès la formulation et produit la conception robuste $\tilde{x}$. La
preuve se lit en **réévaluant $x_0$, $x^\star$ et $\tilde{x}$ sous les mêmes
incertitudes sur le vrai modèle** : seul $\tilde{x}$ respecte toutes les contraintes
à $\geq$ 98 %, là où $x^\star$ tombe à 0,6 % sur la vitesse d'approche, et ce pour un
surcoût de seulement +361 kg ($+0,6\,\%$) sur $x^\star$. La robustesse n'est donc
pas un sur-dimensionnement coûteux mais un léger déplacement du même $x$ vers
l'intérieur du domaine faisable.

**Bilan d'ensemble.** Les deux cas d'usage atteignent des masses nominales très
proches, mais leurs compromis de conception et leurs risques diffèrent : le kérosène
est dimensionné par le décollage et la structure, l'hydrogène par l'approche et le
réservoir cryogénique. Au-delà des chiffres, le projet illustre une méthodologie
robuste : **construire un surrogate simple, le valider rigoureusement, ne s'en
servir que pour chercher, et toujours vérifier sur le vrai modèle**, en intégrant
les incertitudes dès la conception plutôt qu'après coup.

---

## Annexe A — Rôles des membres du groupe

| Membre | Contributions principales |
|:---|:---|
| Paul Louka | Partie 3 cas d'usage 2 (pipeline robuste hydrogène), vue d'ensemble et conclusion |
| Driss Chraibi | Partie 1 (optimisation déterministe) |
| Yasmine Bennaceur | Partie 3 cas d'usage 1, Partie 1 |
| Sarah Procope | Partie 2 (quantification des incertitudes) |

## Annexe B — Utilisation de l'IA

Un assistant IA (Claude) a été utilisé comme outil d'appui, sous supervision et
relecture des auteurs, pour :

- la **réorganisation et l'unification du code** (factorisation du module partagé
  `_oad.py`, harmonisation des scripts par problème, nettoyage des commentaires) ;
- l'**aide à la rédaction et à la structuration du rapport** (mise en forme
  Markdown, cohérence des notations, synthèses) et la **correction
  orthographique** ;
- la **vérification de cohérence** entre les résultats produits par les scripts et
  les valeurs citées dans le rapport.

Les choix de modélisation, les formulations des problèmes, les analyses physiques et
l'interprétation des résultats relèvent des auteurs. Tous les résultats numériques
proviennent de l'exécution des scripts du projet.
