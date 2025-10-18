import numpy as np
import rasterio
from rasterio.transform import from_origin
import os


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


def fusionner_geotiff_multisources(liste_fichiers_sources, fichier_sortie="fusion.tif"):
    """
    Fusionne plusieurs GeoTIFF en un seul fichier multi-bandes.
    Le premier fichier sert de référence pour les métadonnées (dimensions, géoréférencement).
    Chaque fichier source devient une bande dans le fichier de sortie.

    Args:
        liste_fichiers_sources: Liste des chemins des fichiers GeoTIFF sources
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
        # Lecture de la première bande de chaque fichier
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

        # Extraction du nom du fichier sans extension pour nommer la bande
        nom_bande = os.path.splitext(os.path.basename(fichier))[0]
        noms_bandes.append(nom_bande)

    if not donnees_bandes:
        print("❌ Aucune donnée valide à fusionner.")
        return

    # 3. Appariement automatique des fichiers par année pour calculer les ratios
    print(f"\n🔢 Appariement automatique et calcul des ratios...")
    print("=" * 60)

    # Organisation des fichiers par saison et année
    fichiers_par_annee = {}

    for i, nom in enumerate(noms_bandes):
        # Extraction de l'année (premier groupe de 4 chiffres)
        import re

        match = re.search(r"(\d{4})", nom)
        if match:
            annee = match.group(1)
            if annee not in fichiers_par_annee:
                fichiers_par_annee[annee] = {}

            # Détection de la saison
            nom_lower = nom.lower()
            if "summer" in nom_lower:
                fichiers_par_annee[annee]["summer"] = i
            elif "winter" in nom_lower:
                fichiers_par_annee[annee]["winter"] = i

    print(f"Années détectées : {sorted(fichiers_par_annee.keys())}")

    donnees_ratios = []
    noms_ratios = []

    # Calcul des ratios pour chaque année où on a les deux saisons
    for annee in sorted(fichiers_par_annee.keys()):
        if (
            "summer" in fichiers_par_annee[annee]
            and "winter" in fichiers_par_annee[annee]
        ):
            idx_summer = fichiers_par_annee[annee]["summer"]
            idx_winter = fichiers_par_annee[annee]["winter"]

            # Calcul du ratio summer / winter
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(
                    donnees_bandes[idx_winter] != 0,
                    donnees_bandes[idx_summer] / donnees_bandes[idx_winter],
                    0,
                )

            donnees_ratios.append(ratio)

            # Nom du ratio simplifié
            nom_source1 = noms_bandes[idx_summer]
            nom_source2 = noms_bandes[idx_winter]

            # Si le nom contient deux années (ex: winter_2022_2023), on garde que la première
            if nom_source2.count("_") >= 2:
                parties = nom_source2.split("_")
                if parties[-1].isdigit() and len(parties[-1]) == 4:
                    nom_source2 = "_".join(parties[:-1])

            nom_ratio = f"ratio_{nom_source1}_{nom_source2}"
            noms_ratios.append(nom_ratio)

            # Calcul des statistiques
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

    # 4. Fusion des données originales et des ratios
    toutes_bandes = donnees_bandes + donnees_ratios
    tous_noms = noms_bandes + noms_ratios
    nb_bandes = len(toutes_bandes)

    pixels = np.array(toutes_bandes, dtype=np.float32)  # float32 pour supporter les NaN

    print(
        f"\n✅ {len(donnees_bandes)} bandes sources + {len(donnees_ratios)} bandes de ratio"
    )
    print(f"Total : {nb_bandes} bandes")
    print(f"Forme du tableau final : {pixels.shape}")

    # 5. Création du fichier GeoTIFF multi-bandes
    print(f"\n💾 Création du fichier de sortie : {fichier_sortie}")
    print("=" * 60)

    with rasterio.open(
        fichier_sortie,
        "w",
        driver="GTiff",
        height=metadata["variableL"],
        width=metadata["variableW"],
        count=nb_bandes,
        dtype=np.float32,  # float32 pour supporter les NaN dans les ratios
        crs=metadata["crs"],
        transform=metadata["transform"],
        compress="lzw",
    ) as dst:
        # Écriture de chaque bande
        for i in range(nb_bandes):
            dst.write(pixels[i], i + 1)

    # 6. Ajout des noms de bandes
    with rasterio.open(fichier_sortie, "r+") as dst:
        for i in range(nb_bandes):
            dst.set_band_description(i + 1, tous_noms[i])

    print(f"\n✅ Fichier '{fichier_sortie}' créé avec succès !")
    print(f"   - Dimensions : {metadata['variableW']} × {metadata['variableL']} pixels")
    print(f"   - Nombre de bandes : {nb_bandes}")
    print(f"   - Bandes sources : {', '.join(noms_bandes)}")
    print(f"   - Bandes ratios : {', '.join(noms_ratios)}")


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


# Exemple d'utilisation
if __name__ == "__main__":
    # Liste des fichiers sources (le premier sert de référence pour les métadonnées)
    # L'ordre n'a pas d'importance, l'appariement se fait automatiquement par année
    fichiers_sources = [
        "summer_2022.tif",
        "summer_2024.tif",
        "winter_2024_2025.tif",
        "winter_2022_2023.tif",
    ]

    print(f"Nombre de fichiers sources : {len(fichiers_sources)}")

    # Fusion des fichiers avec appariement automatique
    fusionner_geotiff_multisources(fichiers_sources, "fusion_multisources.tif")

    # Affichage des informations du fichier créé
    afficher_info_geotiff("fusion_multisources.tif")
