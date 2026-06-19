# Conclusion

Ce projet a appliqué la conception globale d'avion (OAD) à un appareil de 150
passagers, en comparant une filière **kérosène** (UC1) et une filière **hydrogène
liquide** (UC2) à travers trois problèmes complémentaires, tous résolus en
remplaçant le modèle vrai — coûteux — par un surrogate validé.

**Partie 1 — Optimisation déterministe.** L'optimisation directe sur le vrai modèle
fournit une référence faisable ($\approx$ 63,1 t pour le kérosène, $\approx$ 63,3 t pour
l'hydrogène), l'algorithme sans gradient `COBYLA` se révélant le plus adapté. Le
**krigeage** est le surrogate le plus précis (R$^{2}$ de test et de validation croisée
$\approx$ 0,99) avec un plan d'expériences modéré. Surtout, optimiser *sur* le surrogate
produit des conceptions plus légères mais **infaisables sur le vrai modèle** (le
kérosène viole la distance de décollage de 130 m), illustrant l'exploitation des
erreurs résiduelles du métamodèle aux contraintes actives : toute solution doit être
**validée sur le vrai modèle**.

**Partie 2 — Quantification des incertitudes.** En figeant la conception et en
propageant les incertitudes technologiques, l'analyse de sensibilité révèle des
verrous différenciés : la variance de la MTOM est gouvernée par la **masse
structurale** (`sef`, > 94 %) pour le kérosène, et par l'**indice gravimétrique du
réservoir cryogénique** (`gi`, $\approx$ 64–72 %) pour l'hydrogène. L'optimisation
déterministe, en allégeant la cellule, **concentre** la sensibilité sur ce verrou
dominant et rend l'optimum nominal fragile : au point optimal hydrogène, la marge de
carburant moyenne devient négative sous incertitudes.

**Partie 3 — Optimisation robuste.** L'optimisation robuste (minimisation de
`E[mtom]` sous contraintes de marge) répond à cette fragilité. Pour l'hydrogène
liquide, la conception déterministe ne respecte la vitesse d'approche et la distance
de décollage que **0,6 %** et **31,6 %** du temps sous incertitudes, tandis que la
conception robuste rétablit **toutes** les fiabilités à $\geq$ 98 %, pour un surcoût de
masse de seulement **+361 kg (+0,6 %)**. La comparaison des méthodes d'estimation
(surrogate, Monte-Carlo, Taylor) confirme la cohérence des résultats, l'approche par
surrogate offrant le meilleur compromis coût/précision.

**Bilan d'ensemble.** Les deux filières atteignent des masses nominales très
proches, mais leurs compromis de conception et leurs risques diffèrent : le kérosène
est dimensionné par le décollage et la structure, l'hydrogène par l'approche et le
réservoir cryogénique. Au-delà des chiffres, le projet illustre une méthodologie
robuste : **construire un surrogate simple, le valider rigoureusement, ne s'en
servir que pour chercher, et toujours vérifier sur le vrai modèle** — en intégrant
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
