import requests
import pandas as pd
from sqlalchemy import create_engine, types, MetaData, Table, Column, Integer

# DB postgre
DB_USER = "admin"
DB_PASSWORD = "motdepasse"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "ma_base_de_donnees"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

villes = [
    "Audierne",
    "Bénodet",
    "Beuzec-Cap-Sizun",
    "Briec",
    "Cléden-Cap-Sizun",
    "Clohars-Fouesnant",
    "Combrit",
    "Concarneau",
    "Douarnenez",
    "Edern",
    "Elliant",
    "Ergué-Gabéric",
    "La Forêt-Fouesnant",
    "Fouesnant",
    "Gouesnach",
    "Goulien",
    "Gourlizon",
    "Guengat",
    "Guiler-sur-Goyen",
    "Guilvinec",
    "Île-Tudy",
    "Le Juch",
    "Kerlaz",
    "Landrévarzec",
    "Landudal",
    "Landudec",
    "Langolen",
    "Locronan",
    "Loctudy",
    "Mahalon",
    "Confort-Meilars",
    "Melgven",
    "Névez",
    "Penmarch",
    "Peumerit",
    "Pleuven",
    "Plobannalec-Lesconil",
    "Plogastel-Saint-Germain",
    "Plogoff",
    "Plogonnec",
    "Plomelin",
    "Plomeur",
    "Plonéis",
    "Plonéour-Lanvern",
    "Plouhinec",
    "Plovan",
    "Plozévet",
    "Pluguffan",
    "Pont-Aven",
    "Pont-Croix",
    "Pont-l'Abbé",
    "Pouldergat",
    "Pouldreuzic",
    "Poullan-sur-Mer",
    "Primelin",
    "Quéménéven",
    "Quimper",
    "Rosporden",
    "Saint-Évarzec",
    "Saint-Jean-Trolimon",
    "Saint-Yvi",
    "Tourch",
    "Treffiagat",
    "Tréguennec",
    "Trégunc",
    "Tréméoc",
    "Tréogat",
]

theme_ids = [
    "shop_craft_office",
    "restaurant",
    "sports",
    "playground",
    "hosting",
    "library",
    "historic",
]

all_data = []
for v in villes:
    r = requests.get("https://geodatamine.fr/boundaries/search", params={"text": v})
    if r.status_code != 200:
        raise SystemExit(f"Erreur {r.status_code}: {r.text}")
    boundaries = r.json()
    if not boundaries:
        print(f"{v} : aucune donnée trouvée")
        continue
    boundary = boundaries[0]
    for theme_id in theme_ids:
        url = f"https://geodatamine.fr/data/{theme_id}/{boundary['id']}?format=geojson"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            features = data.get("features", [])
            for feature in features:
                geom = feature.get("geometry", {})
                props = feature.get("properties", {})
                if geom.get("type") == "Point":
                    lon, lat = geom.get("coordinates", [None, None])
                    place_type = props.get("type")
                    if lat is not None and lon is not None:
                        all_data.append(
                            {
                                "theme": theme_id,
                                "type": place_type,
                                "latitude": lat,
                                "longitude": lon,
                            }
                        )
            print(f"{len(features)}  {theme_id}  {v} ok")
        else:
            print(f"Erreur {r.status_code} {theme_id} {v}: {r.text}")

if all_data:
    # Création du DataFrame
    df = pd.DataFrame(all_data)

    metadata = MetaData()
    table = Table(
        "geodata_points",
        metadata,
        Column(
            "id", Integer, primary_key=True, autoincrement=True
        ),  # id unique autoincr
        Column("theme", types.TEXT),
        Column("type", types.TEXT),
        Column("latitude", types.FLOAT),
        Column("longitude", types.FLOAT),
        extend_existing=True,
    )
    metadata.create_all(engine)
    df.to_sql("geodata_points", engine, if_exists="append", index=False)

    print(
        f"{len(df)} lignes insérées dans la table 'geodata_points' avec id auto-incrémenté."
    )
else:
    print("no data")
