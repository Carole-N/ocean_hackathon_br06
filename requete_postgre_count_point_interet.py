import psycopg2
from psycopg2 import sql
import pandas as pd
import numpy as np


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
        dict: Dictionnaire avec les comptes par thème et le total
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

        result_dict = {}
        somme = 0
        for item in results:
            result_dict[item[0]] = item[1]
            somme += item[1]
        result_dict["total"] = somme
        return result_dict

    except Exception as e:
        print(f"Erreur : {e}")
        return {"total": 0}  # Retourne un dict avec total=0 en cas d'erreur

    finally:
        # Fermeture de la connexion
        if "conn" in locals():
            conn.close()


def boucle(db_params):
    """
    Parcourt la grille et compte les points d'intérêt dans chaque cellule.
    Parcours : 91 lignes (latitude décroissante) × 234 colonnes (longitude croissante)

    Args:
        db_params (dict): Paramètres de connexion à la base de données

    Returns:
        tuple: (DataFrame simple (id, total), array 2D pour GeoTIFF)
    """
    lat_init = 48.131249785049995
    lon_init = -4.752082891349997
    lat_step = 0.0041666667
    lon_step = 0.0041666667
    nb_row = 91  # Lignes (latitude)
    nb_col = 234  # Colonnes (longitude)

    list_points = []

    # Array 2D : (91 lignes, 234 colonnes)
    grid_totals = np.zeros((nb_row, nb_col), dtype=np.float32)

    lat = lat_init
    id_cell = 0

    for i in range(nb_row):  # Parcours des lignes (latitude décroissante)
        lon = lon_init
        for j in range(nb_col):  # Parcours des colonnes (longitude croissante)
            # Requête pour cette cellule
            counts = somme_items_dans_zone(lat, lon, lon_step, lat_step, db_params)

            # Stockage du total dans la grille 2D : grid[ligne, colonne]
            total = counts.get("total", 0)
            grid_totals[i, j] = total

            # CSV simple : seulement (id, total)
            list_points.append({"id": id_cell, "total": total})

            lon += lon_step  # Longitude croissante (vers l'est)
            id_cell += 1

        lat -= lat_step  # Latitude décroissante (vers le sud)
        print(f"Ligne {i+1}/{nb_row} traitée")

    # Création du DataFrame
    df = pd.DataFrame(list_points)
    df.to_csv("grille.csv", index=False)
    print(f"\n✅ Résultats sauvegardés dans 'grille.csv'")
    print(f"   - {len(list_points)} cellules traitées")
    print(f"   - Grille: {nb_row} lignes × {nb_col} colonnes")
    print(f"   - Total de points: {df['total'].sum():.0f}")

    return df, grid_totals


def get_points_interet_grid(db_params):
    """
    Fonction wrapper pour obtenir uniquement la grille 2D (pour intégration GeoTIFF).

    Args:
        db_params (dict): Paramètres de connexion à la base de données

    Returns:
        np.array: Array 2D (91, 234) avec les totaux de points d'intérêt
    """
    _, grid = boucle(db_params)
    return grid


# Exemple d'utilisation
if __name__ == "__main__":
    db_params = {
        "host": "localhost",
        "database": "ma_base_de_donnees",
        "user": "admin",
        "password": "motdepasse",
        "port": "5432",
    }

    df, grid = boucle(db_params)

    print(f"\n📊 Statistiques de la grille:")
    print(f"   - Min: {grid.min()}")
    print(f"   - Max: {grid.max()}")
    print(f"   - Moyenne: {grid.mean():.2f}")
    print(f"   - Cellules non-vides: {(grid > 0).sum()}")
