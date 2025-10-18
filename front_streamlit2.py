import streamlit as st
import folium
from folium.raster_layers import ImageOverlay
import rasterio
import numpy as np
from streamlit_folium import st_folium


def run_streamlit(
    latitude: float, longitude: float, H: float, L: float, tif_path: str, bandes_names
):
    if not bandes_names:
        bandes_names = ["1", "2", "3", "4", "5", "6"]

    st.set_page_config(layout="wide")
    st.title("Comparaison de deux cartes avec couches raster (TIF)")

    # Calcul des limites de la carte (rectangle)
    lat_min = latitude - H
    lat_max = latitude
    lon_min = longitude
    lon_max = longitude + L

    # Lire le fichier TIF
    with rasterio.open(tif_path) as src:
        bands = [src.read(i) for i in range(1, src.count + 1)]
        bounds = list(src.bounds)
        folium_bounds = [
            [bounds[1], bounds[0]],
            [bounds[3], bounds[2]],
        ]  # [[lat_min, lon_min], [lat_max, lon_max]]

    # Disposition : 4 colonnes (contrôles gauche | carte gauche | carte droite | contrôles droite)
    col_ctrl_left, col_map_left, col_map_right, col_ctrl_right = st.columns(
        [1, 3, 3, 1]
    )

    # Sélection bandes carte gauche
    with col_ctrl_left:
        st.header("Couches - Carte gauche")
        show_bands_left = [
            st.checkbox(f"{bandes_names[i]}", value=False, key=f"left_{i}")
            for i in range(6)
        ]

    # Sélection bandes carte droite
    with col_ctrl_right:
        st.header("Couches - Carte droite")
        show_bands_right = [
            st.checkbox(f"{bandes_names[i]}", value=False, key=f"right_{i}")
            for i in range(6)
        ]

    # Création carte gauche
    with col_map_left:
        m_left = folium.Map(
            location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2],
            zoom_start=10,
            tiles="OpenStreetMap",
        )
        folium.Rectangle(
            bounds=[[lat_min, lon_min], [lat_max, lon_max]],
            color="transparent",
            fill=False,
            fill_color="transparent",
            fill_opacity=0.1,
        ).add_to(m_left)

        for i, (band, show) in enumerate(zip(bands, show_bands_left)):
            if show:
                band_norm = (band - band.min()) / (band.max() - band.min()) * 255
                band_rgb = np.stack([band_norm.astype(np.uint8)] * 3, axis=-1)
                ImageOverlay(
                    image=band_rgb,
                    bounds=folium_bounds,
                    name=bandes_names[i],
                    opacity=0.5,
                ).add_to(m_left)

        folium.LayerControl().add_to(m_left)
        st_folium(m_left, width=700, height=500, key="map_left")

    # Création carte droite
    with col_map_right:
        m_right = folium.Map(
            location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2],
            zoom_start=10,
            tiles="OpenStreetMap",
        )
        folium.Rectangle(
            bounds=[[lat_min, lon_min], [lat_max, lon_max]],
            color="transparent",
            fill=False,
            fill_color="transparent",
            fill_opacity=0.1,
        ).add_to(m_right)

        for i, (band, show) in enumerate(zip(bands, show_bands_right)):
            if show:
                band_norm = (band - band.min()) / (band.max() - band.min()) * 255
                band_rgb = np.stack([band_norm.astype(np.uint8)] * 3, axis=-1)
                ImageOverlay(
                    image=band_rgb,
                    bounds=folium_bounds,
                    name=bandes_names[i],
                    opacity=0.5,
                ).add_to(m_right)

        folium.LayerControl().add_to(m_right)
        st_folium(m_right, width=700, height=500, key="map_right")


def main():
    latitude = 48.13
    longitude = -4.75
    H = 0.4
    L = 1
    tif_path = "fusion_multisources.tif"
    bandes_names = [
        "summer_2022",
        "winter_2022_23",
        "ratio_2022",
        "summer_2024",
        "winter_2024_25",
        "ratio_2024",
    ]
    run_streamlit(latitude, longitude, H, L, tif_path, bandes_names)


if __name__ == "__main__":
    main()
