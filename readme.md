# Projet GouloùNoz

Porjet Bre06 du Ocean Hackathon 2025

## installation

création d'une VM :
dans le terminal, lancer `python3 -m venv .venv`

lancement de la VM
dans le terminal, lancer `source .venv/bin/activate`

Récupérer les dépendances
dans le terminal, lancer `pip install -r requirements.txt`

## Lancement d'une base de données PostGre (dans Docker)

dans le terminal, lancer `docker-compose up -d`

## Récupération des données touristiques

lancer le fichier `scrappingOsm` : `python3 scrappingOsm.py`

## Création d'une image Tif multilayer avec les données

lancer le fichier `scrappingOsm` : `python3 test_create_tif_source.py`
(ce fichier importe les fonctions de requete_postgre)
