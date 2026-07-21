# Note d'analyse & de renseignement — TASS « Guerre »

> Squelette à compléter après une exécution réelle du pipeline sur le vrai
> corpus et un cluster Elastic Cloud réel. Aucun chiffre ni screenshot ici
> n'est fabriqué : ce fichier est volontairement vide de résultats — à
> reporter ensuite dans le template PDF officiel du cours.

## 1. Lien GitHub

<https://github.com/louischef/AIDeployment>

## 2. Périmètre des données

- Nombre d'articles bruts (`data/raw/articles.json`) :
- Nombre d'articles retenus après extraction (`data/interim/corpus.jsonl`) :
- Période couverte (date min / date max) :

## 3. Annotation

- Nombre d'articles annotés :
- Nombre d'entités par label (WEAPON / MIL_UNIT / MIL_ORG) :
- Échantillon revu manuellement (`review_log.json`) : ___ articles, ___ % acceptés sans modification
- Écarts constatés pendant la revue et gazetteers étendus en conséquence :

## 4. Modèle

- Split train / dev :
- Métriques `spacy train` (precision / recall / F-score par label — voir
  `output/model-best/meta.json` ou les logs de `spacy train`) :
- Limites observées à l'inférence (étape 4 — « Que constatez-vous ? ») :

## 5. Dashboards Kibana

(Insérer ici les screenshots : top WEAPON, top MIL_UNIT, top MIL_ORG,
histogramme temporel des mentions.)

- Choix de visualisation et justification :
- Lecture des tendances observées :

## 6. Note de renseignement (courte)

> Rappel du cadre OSINT (slide 6) : TASS est un média d'État russe. Ce qui
> suit reflète ce que la source affirme, pas une vérité vérifiée.

- Constat principal :
- Fiabilité / limites de la source :
- Ce que ces données permettent — et ne permettent pas — de conclure :
