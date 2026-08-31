"""
Dashboard "Rionegro, Quebrada Yarumal"

Estudiante: Juan José Gallo
Estación fija: 5
Nombre: Rionegro,Quebrada Yarumal

Para correr:
    streamlit run app_nivel_cornare.py
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ================================================================
# CONFIGURACIÓN DE MI ESTACIÓN
# ================================================================

NOMBRE_ESTUDIANTE = "Juan José Gallo"

CODIGO_ESTACION = "5"

NOMBRE_ESTACION = "Rionegro, Quebrada Yarumal"

UBICACION_ESTACION = "Vereda Yarumal, Rionegro, Antioquia"

# Coordenadas de la estación 5
LAT_ESTACION = 6.1733
LON_ESTACION = -75.4552

# Altitud de la estación.
# Si CORNARE/API entrega una altitud específica, reemplazar este valor.
ALTITUD_ESTACION = 2140


API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

LLAVE_FECHA = "level_date"
LLAVE_VALOR = "level"


# Posibles nombres de las coordenadas si la API las entrega
CANDIDATOS_LAT = [
    "lat",
    "latitude",
    "latitud",
]

CANDIDATOS_LON = [
    "lng",
    "lon",
    "longitude",
    "longitud",
]


# ================================================================
# CONFIGURACIÓN DE STREAMLIT
# ================================================================

st.set_page_config(
    page_title="Nivel — Rionegro Quebrada Yarumal",
    page_icon="😎",
    layout="wide"
)


# ================================================================
# FUNCIONES DE CONSULTA
# ================================================================

def obtener_serie_nivel(
    codigo_estacion,
    desde,
    hasta,
    calidad=1,
    timeout=30
):

    url = f"{API_BASE_URL}/{codigo_estacion}/nivel"

    params = {
        "desde": desde,
        "hasta": hasta,
        "calidad": calidad
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    try:

        resp = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            verify=False
        )

        if resp.status_code == 200:
            return resp.json(), None

        return None, f"HTTP {resp.status_code}"

    except requests.exceptions.RequestException as e:

        return None, f"Error de red: {e}"


# ================================================================
# PAGINACIÓN
# ================================================================

def obtener_todas_las_paginas(datos_json, timeout=30):

    registros = list(datos_json.get("values", []))

    siguiente_url = datos_json.get("next")

    while siguiente_url:

        try:

            resp = requests.get(
                siguiente_url,
                timeout=timeout,
                verify=False
            )

        except requests.exceptions.RequestException:

            break

        if resp.status_code != 200:
            break

        pagina = resp.json()

        registros.extend(
            pagina.get("values", [])
        )

        siguiente_url = pagina.get("next")

    return registros


# ================================================================
# DETECTAR COORDENADAS
# ================================================================

def detectar_coordenadas(datos_json):

    """
    Primero intenta obtener coordenadas desde la API.

    Si la API no las entrega, utiliza las coordenadas
    conocidas de la estación 5.
    """

    if not isinstance(datos_json, dict):

        return (
            LAT_ESTACION,
            LON_ESTACION,
            False
        )

    lat = next(
        (
            datos_json[k]
            for k in CANDIDATOS_LAT
            if k in datos_json
        ),
        None
    )

    lon = next(
        (
            datos_json[k]
            for k in CANDIDATOS_LON
            if k in datos_json
        ),
        None
    )

    if lat is not None and lon is not None:

        try:

            return (
                float(lat),
                float(lon),
                True
            )

        except (TypeError, ValueError):

            pass

    return (
        LAT_ESTACION,
        LON_ESTACION,
        False
    )


# ================================================================
# ÍNDICE DE CALIDAD
# ================================================================

def calcular_indice_calidad(df):

    """
    Índice simple de calidad:

    - 70% completitud de la serie
    - 30% ausencia de outliers
    """

    if df.empty or len(df) < 2:

        return 0.0, 0, 0

    df_idx = df.set_index("fecha")

    frecuencia_tipica = (
        df["fecha"]
        .diff()
        .dropna()
        .mode()
    )

    if len(frecuencia_tipica) == 0:

        return 0.0, 0, 0

    frecuencia_tipica = frecuencia_tipica[0]

    rango_completo = pd.date_range(
        start=df_idx.index.min(),
        end=df_idx.index.max(),
        freq=frecuencia_tipica
    )

    esperados = len(rango_completo)

    huecos = esperados - len(df_idx)

    completitud = (
        max(
            0.0,
            1 - (huecos / esperados)
        )
        if esperados > 0
        else 0.0
    )

    Q1 = df["nivel"].quantile(0.25)
    Q3 = df["nivel"].quantile(0.75)

    IQR = Q3 - Q1

    lim_inf = Q1 - 1.5 * IQR
    lim_sup = Q3 + 1.5 * IQR

    es_outlier = (
        (df["nivel"] < lim_inf)
        |
        (df["nivel"] > lim_sup)
        |
        (df["nivel"] < 0)
    )

    proporcion_outliers = es_outlier.mean()

    indice = (
        completitud * 0.7
        +
        (1 - proporcion_outliers) * 0.3
    ) * 100

    return (
        round(indice, 1),
        int(huecos),
        int(es_outlier.sum())
    )


# ================================================================
# SIDEBAR
# ================================================================

st.sidebar.title(" Mi estación")

st.sidebar.success(
    f"Estudiante: {NOMBRE_ESTUDIANTE}"
)

st.sidebar.subheader("Datos de la estación")

# Código fijo: estación 5
st.sidebar.text_input(
    "Código de estación",
    value=CODIGO_ESTACION,
    disabled=True
)

st.sidebar.text_input(
    "Nombre de estación",
    value=NOMBRE_ESTACION,
    disabled=True
)

st.sidebar.text_input(
    "Ubicación",
    value=UBICACION_ESTACION,
    disabled=True
)

st.sidebar.subheader("Parámetros de consulta")

fecha_desde = st.sidebar.date_input(
    "Desde",
    pd.to_datetime("2026-08-25")
).strftime("%Y-%m-%d")

fecha_hasta = st.sidebar.date_input(
    "Hasta",
    pd.to_datetime("2026-08-31")
).strftime("%Y-%m-%d")

calidad = st.sidebar.selectbox(
    "Calidad",
    [1, 0],
    index=0,
    help="1 = solo datos validados"
)

consultar = st.sidebar.button(
    "🔍 Consultar estación",
    type="primary"
)


# ================================================================
# ENCABEZADO
# ================================================================

st.title(
    "🌊 Nivel de ríos y quebradas — CORNARE"
)

st.caption(
    f"Estudiante: **{NOMBRE_ESTUDIANTE}** "
    f"· Estación **{CODIGO_ESTACION}** "
    f"· **{NOMBRE_ESTACION}**"
)


# ================================================================
# INFORMACIÓN DE LA ESTACIÓN
# ================================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Código",
    CODIGO_ESTACION
)

col2.metric(
    "Latitud",
    f"{LAT_ESTACION:.4f}"
)

col3.metric(
    "Longitud",
    f"{LON_ESTACION:.4f}"
)

col4.metric(
    "Altitud",
    f"{ALTITUD_ESTACION:,} m s. n. m."
)


st.info(
    f"📍 **{NOMBRE_ESTACION}** · "
    f"{UBICACION_ESTACION}"
)


# ================================================================
# CONSULTA
# ================================================================

if consultar:

    with st.spinner(
        "Consultando información de la estación 5..."
    ):

        datos_crudos, error = obtener_serie_nivel(
            CODIGO_ESTACION,
            fecha_desde,
            fecha_hasta,
            calidad
        )

    if error:

        st.error(
            f"❌ {error}"
        )

    else:

        registros = obtener_todas_las_paginas(
            datos_crudos
        )

        if not registros:

            st.warning(
                "No hay registros para la estación 5 "
                "en el rango de fechas seleccionado."
            )

        else:

            # ====================================================
            # DATAFRAME
            # ====================================================

            df = pd.DataFrame(registros)

            df = df.rename(
                columns={
                    LLAVE_FECHA: "fecha",
                    LLAVE_VALOR: "nivel"
                }
            )

            df["fecha"] = pd.to_datetime(
                df["fecha"],
                errors="coerce"
            )

            df["nivel"] = pd.to_numeric(
                df["nivel"],
                errors="coerce"
            )

            df = (
                df
                .dropna(
                    subset=[
                        "fecha",
                        "nivel"
                    ]
                )
                .sort_values("fecha")
                .reset_index(drop=True)
            )


            # ====================================================
            # COORDENADAS
            # ====================================================

            lat, lon, coords_reales = detectar_coordenadas(
                datos_crudos
            )


            # ====================================================
            # CALIDAD
            # ====================================================

            indice_calidad, huecos, n_outliers = (
                calcular_indice_calidad(df)
            )


            # ====================================================
            # MÉTRICAS
            # ====================================================

            st.subheader(
                " Información de la estación"
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Lecturas",
                len(df)
            )

            col2.metric(
                "Nivel promedio",
                f"{df['nivel'].mean():.2f} cm"
            )

            col3.metric(
                "Nivel actual",
                f"{df['nivel'].iloc[-1]:.2f} cm"
            )

            col4.metric(
                "Índice de calidad",
                f"{indice_calidad} / 100"
            )


            # ====================================================
            # GRÁFICO
            # ====================================================

            st.subheader(
                "📈 Nivel de la quebrada Yarumal"
            )

            st.line_chart(
                df.set_index("fecha")["nivel"],
                y_label="Nivel (cm)",
                x_label="Fecha"
            )


            # ====================================================
            # UBICACIÓN
            # ====================================================

            st.subheader(
                " Ubicación de la estación"
            )

            col1, col2 = st.columns([2, 1])

            with col1:

                mapa = pd.DataFrame(
                    {
                        "lat": [lat],
                        "lon": [lon]
                    }
                )

                st.map(
                    mapa,
                    zoom=12
                )

            with col2:

                st.markdown(
                    f"""
                    ### {NOMBRE_ESTACION}

                    **Código:** {CODIGO_ESTACION}

                    **Municipio:** Rionegro

                    **Departamento:** Antioquia

                    **Ubicación:** {UBICACION_ESTACION}

                    **Latitud:** {lat:.4f}

                    **Longitud:** {lon:.4f}

                    **Altitud:** {ALTITUD_ESTACION:,} m s. n. m.
                    """
                )

                if coords_reales:

                    st.success(
                        "✓ Coordenadas obtenidas desde la API"
                    )

                else:

                    st.info(
                        "Coordenadas configuradas para la estación 5."
                    )


            # ====================================================
            # CALIDAD
            # ====================================================

            with st.expander(
                "🔎 Detalle del índice de calidad"
            ):

                st.write(
                    f"- Huecos de reporte detectados: "
                    f"**{huecos}**"
                )

                st.write(
                    f"- Outliers detectados: "
                    f"**{n_outliers}** de "
                    f"**{len(df)}** lecturas"
                )

                st.write(
                    "El índice combina completitud de la "
                    "serie (70%) y proporción de datos "
                    "sin outliers (30%)."
                )


            # ====================================================
            # DATOS
            # ====================================================

            with st.expander(
                "📋 Ver datos de la estación"
            ):

                st.dataframe(
                    df,
                    use_container_width=True
                )


            # ====================================================
            # DESCARGA
            # ====================================================

            csv = df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Descargar datos CSV",
                csv,
                file_name=(
                    "nivel_estacion_5_"
                    "rionegro_yarumal.csv"
                ),
                mime="text/csv"
            )


else:

    st.info(
        "👈 Ajusta las fechas y la calidad en el "
        "sidebar y presiona **Consultar estación**."
    )
