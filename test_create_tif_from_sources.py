import numpy as np
import rasterio
from rasterio.transform import from_origin
import os
import requete_postgre_count_point_interet


def lire_metadata_geotiff(tif_file):
    """
    Lit les métadonnées d'un fichier GeoTIFF et extrait les variables géospatiales.

    Args:
        tif_file: Chemin vers le fichier GeoTIFF

    Returns:
        dict: Dictionnaire contenant les variables extraites
    """
    try:
        with rasterio.open(tif_file) as src:
            # Dimensions de l'image
            variableW = src.width
            variableL = src.height

            # Transformation affine
            transform = src.transform

            # Coin supérieur gauche (origine)
            variableLong = transform.c  # Longitude (x)
            variableLat = transform.f  # Latitude (y)

            # Résolution des pixels
            variablePixLong = transform.a  # Résolution en x (longitude)
            variablePixLat = abs(
                transform.e
            )  # Résolution en y (latitude, valeur absolue)

            # Informations supplémentaires
            crs = src.crs
            dtype = src.dtypes[0]

            # Affichage des informations lues
            print(f"\n📖 Lecture du fichier de référence : {tif_file}")
            print("=" * 60)
            print(f"Dimensions : {variableW} × {variableL} pixels")
            print(f"Coin supérieur gauche : ({variableLong}, {variableLat})")
            print(f"Résolution : {variablePixLong} × {variablePixLat}")
            print(f"CRS : {crs}")
            print(f"Type de données : {dtype}")

            # Retour des variables
            variables = {
                "variableW": variableW,
                "variableL": variableL,
                "variableLong": variableLong,
                "variableLat": variableLat,
                "variablePixLong": variablePixLong,
                "variablePixLat": variablePixLat,
                "crs": str(crs),
                "dtype": dtype,
                "transform": transform,
            }

            return variables

    except FileNotFoundError:
        print(f"❌ Erreur : Le fichier '{tif_file}' est introuvable.")
        return None
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return None


def lire_bande_geotiff(nom_fichier_tiff, bande=1):
    """
    Lit les données d'une bande spécifique d'un GeoTIFF.

    Args:
        nom_fichier_tiff: Nom du fichier GeoTIFF
        bande: Numéro de la bande à lire (par défaut: 1)

    Returns:
        numpy.array: Tableau 2D contenant les données de la bande
    """
    try:
        with rasterio.open(nom_fichier_tiff) as src:
            data = src.read(bande)
            print(
                f"  ✓ {nom_fichier_tiff} - Bande {bande} : {data.shape}, min={data.min():.2f}, max={data.max():.2f}"
            )
            return data
    except Exception as e:
        print(f"  ✗ Erreur lors de la lecture de {nom_fichier_tiff} : {e}")
        return None


def afficher_info_geotiff(nom_fichier):
    """
    Affiche les informations détaillées d'un GeoTIFF multi-bandes.

    Args:
        nom_fichier: Nom du fichier GeoTIFF
    """
    try:
        with rasterio.open(nom_fichier) as src:
            print(f"\n📄 Informations sur : {nom_fichier}")
            print("=" * 60)
            print(f"Dimensions : {src.width} × {src.height} pixels")
            print(f"Nombre de bandes : {src.count}")
            print(f"Type de données : {src.dtypes[0]}")
            print(f"CRS : {src.crs}")
            print(f"Transform : {src.transform}")

            print(f"\nDétail des bandes :")
            for i in range(1, src.count + 1):
                description = src.descriptions[i - 1] or f"Bande_{i}"
                data = src.read(i)
                print(
                    f"  Bande {i} ({description}) : min={data.min():.2f}, max={data.max():.2f}, mean={data.mean():.2f}"
                )

    except Exception as e:
        print(f"❌ Erreur : {e}")


def fusionner_geotiff_multisources(
    liste_fichiers_sources, db_params, fichier_sortie="fusion.tif"
):
    """
    Fusionne plusieurs GeoTIFF en un seul fichier multi-bandes.
    Ajoute automatiquement une couche "points d'intérêt" depuis la base de données.

    Args:
        liste_fichiers_sources: Liste des chemins des fichiers GeoTIFF sources
        db_params: Paramètres de connexion PostgreSQL pour les points d'intérêt
        fichier_sortie: Nom du fichier GeoTIFF de sortie
    """
    if not liste_fichiers_sources:
        print("❌ Erreur : La liste des fichiers sources est vide.")
        return

    # 1. Lecture des métadonnées du premier fichier (fichier de référence)
    fichier_reference = liste_fichiers_sources[0]
    metadata = lire_metadata_geotiff(fichier_reference)

    if metadata is None:
        print("❌ Impossible de lire le fichier de référence.")
        return

    # 2. Lecture des données de chaque fichier source
    print(
        f"\n📥 Lecture des données des {len(liste_fichiers_sources)} fichiers sources..."
    )
    print("=" * 60)

    donnees_bandes = []
    noms_bandes = []

    for fichier in liste_fichiers_sources:
        data = lire_bande_geotiff(fichier, bande=1)

        if data is None:
            print(f"⚠️  Fichier ignoré : {fichier}")
            continue

        # Vérification des dimensions
        if data.shape != (metadata["variableL"], metadata["variableW"]):
            print(
                f"⚠️  Attention : {fichier} a des dimensions différentes ({data.shape}) - ignoré"
            )
            continue

        donnees_bandes.append(data)
        nom_bande = os.path.splitext(os.path.basename(fichier))[0]
        noms_bandes.append(nom_bande)

    if not donnees_bandes:
        print("❌ Aucune donnée valide à fusionner.")
        return

    # 3. 🆕 AJOUT DE LA COUCHE POINTS D'INTÉRÊT
    print(f"\n📍 Récupération des points d'intérêt depuis PostgreSQL...")
    print("=" * 60)

    try:
        # Appel de la fonction pour récupérer la grille
        data_poi = requete_postgre_count_point_interet.get_points_interet_grid(
            db_params
        )

        # Vérification des dimensions
        expected_shape = (metadata["variableL"], metadata["variableW"])
        if data_poi.shape != expected_shape:
            print(
                f"⚠️  ATTENTION: Dimensions de la grille POI {data_poi.shape} != dimensions GeoTIFF {expected_shape}"
            )
            print(
                f"   La couche POI sera tout de même ajoutée, mais vérifiez la cohérence spatiale !"
            )

        # Ajout à la liste des bandes
        donnees_bandes.append(data_poi.astype(np.float32))
        noms_bandes.append("points_interet")

        # Statistiques
        print(f"  ✓ Grille POI ajoutée : {data_poi.shape}")
        print(
            f"    Min={data_poi.min():.0f}, Max={data_poi.max():.0f}, Mean={data_poi.mean():.2f}"
        )
        print(f"    Cellules avec POI : {(data_poi > 0).sum()} / {data_poi.size}")

    except Exception as e:
        print(f"  ✗ Erreur lors de la récupération des POI : {e}")
        print(f"  Le fichier sera créé sans la couche points d'intérêt.")

    # 4. Appariement automatique des fichiers par année pour calculer les ratios
    print(f"\n🔢 Appariement automatique et calcul des ratios...")
    print("=" * 60)

    fichiers_par_annee = {}

    for i, nom in enumerate(noms_bandes):
        # Skip la bande points_interet pour le calcul des ratios
        if nom == "points_interet":
            continue

        import re

        match = re.search(r"(\d{4})", nom)
        if match:
            annee = match.group(1)
            if annee not in fichiers_par_annee:
                fichiers_par_annee[annee] = {}

            nom_lower = nom.lower()
            if "summer" in nom_lower:
                fichiers_par_annee[annee]["summer"] = i
            elif "winter" in nom_lower:
                fichiers_par_annee[annee]["winter"] = i

    print(f"Années détectées : {sorted(fichiers_par_annee.keys())}")

    donnees_ratios = []
    noms_ratios = []

    for annee in sorted(fichiers_par_annee.keys()):
        if (
            "summer" in fichiers_par_annee[annee]
            and "winter" in fichiers_par_annee[annee]
        ):
            idx_summer = fichiers_par_annee[annee]["summer"]
            idx_winter = fichiers_par_annee[annee]["winter"]

            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(
                    donnees_bandes[idx_winter] != 0,
                    donnees_bandes[idx_summer] / donnees_bandes[idx_winter],
                    0,
                )

            donnees_ratios.append(ratio)

            nom_source1 = noms_bandes[idx_summer]
            nom_source2 = noms_bandes[idx_winter]

            if nom_source2.count("_") >= 2:
                parties = nom_source2.split("_")
                if parties[-1].isdigit() and len(parties[-1]) == 4:
                    nom_source2 = "_".join(parties[:-1])

            nom_ratio = f"ratio_{nom_source1}_{nom_source2}"
            noms_ratios.append(nom_ratio)

            ratio_min = ratio.min()
            ratio_max = ratio.max()
            ratio_mean = ratio.mean()
            nb_zeros = (ratio == 0).sum()

            print(f"  ✓ Année {annee}: {nom_ratio}")
            print(f"    {noms_bandes[idx_summer]} / {noms_bandes[idx_winter]}")
            print(
                f"    Min={ratio_min:.4f}, Max={ratio_max:.4f}, Mean={ratio_mean:.4f}"
            )
            print(f"    Pixels à 0 (division par zéro) : {nb_zeros}")
        else:
            saisons_manquantes = []
            if "summer" not in fichiers_par_annee[annee]:
                saisons_manquantes.append("summer")
            if "winter" not in fichiers_par_annee[annee]:
                saisons_manquantes.append("winter")
            print(
                f"  ⚠️  Année {annee}: saison(s) manquante(s) - {', '.join(saisons_manquantes)}"
            )

    # 5. Fusion des données originales et des ratios
    toutes_bandes = donnees_bandes + donnees_ratios
    tous_noms = noms_bandes + noms_ratios
    nb_bandes = len(toutes_bandes)

    pixels = np.array(toutes_bandes, dtype=np.float32)

    print(
        f"\n✅ {len(donnees_bandes)} bandes sources + {len(donnees_ratios)} bandes de ratio"
    )
    print(f"Total : {nb_bandes} bandes (incluant points_interet)")
    print(f"Forme du tableau final : {pixels.shape}")

    # 6. Création du fichier GeoTIFF multi-bandes
    print(f"\n💾 Création du fichier de sortie : {fichier_sortie}")
    print("=" * 60)

    with rasterio.open(
        fichier_sortie,
        "w",
        driver="GTiff",
        height=metadata["variableL"],
        width=metadata["variableW"],
        count=nb_bandes,
        dtype=np.float32,
        crs=metadata["crs"],
        transform=metadata["transform"],
        compress="lzw",
    ) as dst:
        for i in range(nb_bandes):
            dst.write(pixels[i], i + 1)

    # 7. Ajout des noms de bandes
    with rasterio.open(fichier_sortie, "r+") as dst:
        for i in range(nb_bandes):
            dst.set_band_description(i + 1, tous_noms[i])

    print(f"\n✅ Fichier '{fichier_sortie}' créé avec succès !")
    print(f"   - Dimensions : {metadata['variableW']} × {metadata['variableL']} pixels")
    print(f"   - Nombre de bandes : {nb_bandes}")
    print(f"   - Bandes sources : {', '.join(noms_bandes)}")
    print(f"   - Bandes ratios : {', '.join(noms_ratios)}")


# Exemple d'utilisation
if __name__ == "__main__":
    fichiers_sources = [
        "summer_2022.tif",
        "summer_2024.tif",
        "winter_2024_2025.tif",
        "winter_2022_2023.tif",
    ]

    # Paramètres de connexion PostgreSQL
    db_params = {
        "host": "localhost",
        "database": "ma_base_de_donnees",
        "user": "admin",
        "password": "motdepasse",
        "port": "5432",
    }

    print(f"Nombre de fichiers sources : {len(fichiers_sources)}")

    # Fusion avec ajout automatique de la couche POI
    fusionner_geotiff_multisources(
        fichiers_sources, db_params, "fusion_multisources.tif"
    )

    # Affichage des informations du fichier créé
    afficher_info_geotiff("fusion_multisources.tif")
