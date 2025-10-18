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

lancer le fichier `create_tif` : `python3 test_create_tif_source.py`
(ce fichier importe les fonctions de requete_postgre)

Les scripts vont créer un fichier csv du total de points d'intérêts par polygones (grille.csv)
et une image Tif multilayers (fusion_multisources.tif)

## Affichage d'un front-end streamlit

Un serveur streamlit peut être lancé pour servir les données en html avec la commande :
`streamlit run front_streamlit2.py`
Ouvrir un navigateur sur le port indiqué.
