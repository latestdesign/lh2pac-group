# Le projet LH2PAC

LH2PAC est un projet académique en Python proposé par Matthias De Lozzo et Thierry Druot
dans le cadre du cours **« Métamodèles »**
du [programme ModIA](https://www.math.insa-toulouse.fr/fr/enseignement/apprentissage-modia.html).

## Installation

### Git

#### Cloner le dépôt (une seule fois)

Dans votre répertoire de travail préféré,
par exemple `"my_wd"` :

```
git clone git@gitlab.com:MatthiasDeLozzo/lh2pac.git
```

Cela créera un répertoire `"lh2pac"` dans `"my_wd"`.

#### Créer une branche de travail (une seule fois)

Dans le répertoire `"lh2pac"` :

```
git checkout origin/modia2026 -b my_modia2026  
```

#### Rebaser votre branche de travail

De temps en temps,
le projet _git_ peut être mis à jour avec des informations supplémentaires ;
il faudra alors rebaser votre branche.

Assurez-vous d'être sur `my_modia2026` ;
sinon : `git checkout my_modia2026`.

Dans le répertoire `"my_wd/lh2pac"` :

```
git fetch origin
git rebase origin/modia2026
```

### Créer un environnement virtuel (une seule fois)

Dans le répertoire `"lh2pac"` :

=== "Linux"

    ```
    python -m venv .venv
    source .venv/bin/activate
    pip install --editable .
    source .venv/bin/deactivate
    ```

=== "Windows"

    ```
    python -m venv .venv
    .venv\Scripts\activate.bat
    pip install --editable .
    .venv\Scripts\deactivate.bat
    ```

### Configurer votre IDE (une seule fois)

Sélectionnez l'interpréteur Python :

=== "Linux"

    `"my_wd/lh2pac/.venv/bin/python"`

=== "Windows"

    `"lh2pac\.venv\Scripts\python.exe"`

### Utiliser l'environnement virtuel dans une console Python

Dans le répertoire `"lh2pac"` :

=== "Linux"

    ```
    source .venv/bin/activate
    ```

=== "Windows"

    ```
    .venv\Scripts\activate.bat
    ```

et utilisez Python normalement.

### Compiler la documentation

#### Compilation à chaque sauvegarde (doc temporaire)

=== "Linux"

    ```
    properdocs serve
    ```

=== "Windows"

    ```
    properdocs.exe serve
    ```

La documentation est générée et accessible à une adresse locale,
par exemple [http://127.0.0.1:8000](http://127.0.0.1:8000).

Ensuite,
à chaque sauvegarde d'un fichier,
la documentation sera mise à jour automatiquement.

#### Compilation définitive (doc permanente)

La commande précédente ne sauvegarde pas le site ;
pour cela, utilisez la commande suivante.

=== "Linux"

    ```
    properdocs build
    ```

=== "Windows"

    ```
    properdocs.exe build
    ```

L'aventure LH2PAC commence ici !
