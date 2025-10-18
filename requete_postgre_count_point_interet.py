import psycopg2
from psycopg2 import sql
import pandas as pd


def somme_items_dans_zone(
    latitude0, longitude0, largeur_de_la_zone, hauteur_de_la_zone, db_params
):
    """
    Calcule la somme des items dans une zone rectangulaire définie par :
    - latitude0, longitude0 : coin haut-gauche
    - largeur_de_la_zone, hauteur_de_la_zone : dimensions en degrés

    Args:
        latitude0 (float): Latitude du coin haut-gauche
        longitude0 (float): Longitude du coin haut-gauche
        largeur_de_la_zone (float): Largeur de la zone en degrés
        hauteur_de_la_zone (float): Hauteur de la zone en degrés
        db_params (dict): Paramètres de connexion à la base de données

    Returns:
        float: Somme des items dans la zone
    """
    # Calcul des bornes de la zone
    lat_max = latitude0
    lat_min = latitude0 - hauteur_de_la_zone
    lon_min = longitude0
    lon_max = longitude0 + largeur_de_la_zone

    try:
        # Connexion à la base de données
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Requête SQL
        query = sql.SQL(
            """
            SELECT theme, COUNT(*) AS nombre_points
            FROM geodata_points
            WHERE latitude BETWEEN %s AND %s
            AND longitude BETWEEN %s AND %s
            GROUP BY theme;
        """
        )

        # Exécution de la requête
        cursor.execute(query, (lat_min, lat_max, lon_min, lon_max))
        results = cursor.fetchall()

        dict = {}
        somme = 0
        for item in results:
            dict[item[0]] = item[1]
            somme += item[1]
        dict["total"] = somme
        return dict

    except Exception as e:
        print(f"Erreur : {e}")
        return None

    finally:
        # Fermeture de la connexion
        if "conn" in locals():
            conn.close()


def boucle():
    id = 0
    lat_init = 48.131249785049995
    lon_init = -4.752082891349997
    lat_step = 0.0041666667
    lon_step = 0.0041666667
    nb_row = 91
    nb_col = 234
    lat = lat_init
    list_points = []
    for i in range(0, nb_row):
        lon = lon_init
        for j in range(0, nb_col):
            somme = somme_items_dans_zone(lat, lon, lat_step, lon_step, db_params)
            lon += lon_step
            id += 1
            list_points.append({id: somme})
        lat += lat_step
        print(i)

    df = pd.DataFrame(list_points)
    df.to_csv("grille.csv", index=False)
    print("Résultats sauvegardés dans 'resultats_grille.csv'.")
    return list_points

# Exemple d'utilisation
db_params = {
    "host": "localhost",
    "database": "ma_base_de_donnees",
    "user": "admin",
    "password": "motdepasse",
    "port": "5432",
}

boucle()
