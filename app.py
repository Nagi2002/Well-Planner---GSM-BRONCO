from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "project_demo.json"
CSS_FILE = BASE_DIR / "assets" / "styles.css"


# ============================================================
# COLORES
# ============================================================

DEFAULT_COLOR = "#5B9BD5"

COLOR_OPTIONS = {
    "🟨 Amarillo": "#FFD966",
    "🟨 Amarillo intenso": "#FFC000",
    "🟩 Verde claro": "#A9D18E",
    "🟩 Verde": "#70AD47",
    "🟢 Verde intenso": "#00B050",
    "🟦 Azul": "#5B9BD5",
    "🔵 Azul oscuro": "#4472C4",
    "⬜ Gris": "#D9D9D9",
    "⬛ Gris oscuro": "#A5A5A5",
    "🟧 Naranja": "#ED7D31",
    "🟪 Morado": "#7030A0",
    "🟥 Rojo": "#C00000",
}

HEX_TO_COLOR_NAME = {
    hex_value.upper(): name
    for name, hex_value in COLOR_OPTIONS.items()
}

COLORS = {
    "Construcción": "#A9D18E",
    "Terminación": "#FFF200",
    "Movilización": "#D9D9D9",
    "Perforación programada": "#FFD966",
    "Perforación real": "#FFC000",
    "Infraestructura": "#7030A0",
    "Completación": "#5B9BD5",
    "Espera": "#BFBFBF",
    "Mantenimiento": "#ED7D31",
}


# ============================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================

st.set_page_config(
    page_title="GSM BRONCO",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

def load_css() -> None:

    if CSS_FILE.exists():
        css_content = CSS_FILE.read_text(
            encoding="utf-8"
        )

        st.markdown(
            f"<style>{css_content}</style>",
            unsafe_allow_html=True,
        )


# ============================================================
# CARGAR PROYECTO
# ============================================================

def load_project() -> dict:

    if not DATA_FILE.exists():

        return {
            "project": {
                "name": "Programa Integral de Equipos 2026",
                "code": "WP-2026-001",
                "manager": "Ingeniería de Pozos",
                "status": "En ejecución",
                "year": 2026,
            },
            "activities": [],
        }

    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# ============================================================
# VALIDAR COLOR
# ============================================================

def validate_hex_color(
    value,
    fallback: str = DEFAULT_COLOR,
) -> str:

    if value is None:
        return fallback

    value = str(value).strip()

    if re.fullmatch(
        r"#[0-9A-Fa-f]{6}",
        value,
    ):
        return value.upper()

    return fallback


# ============================================================
# NORMALIZAR ACTIVIDADES
# ============================================================

def normalize(
    df: pd.DataFrame,
) -> pd.DataFrame:

    required_columns = [
        "id",
        "rig",
        "capacity_hp",
        "schedule_type",
        "well",
        "activity_type",
        "label",
        "color",
        "start_date",
        "end_date",
        "progress",
        "critical",
    ]

    if df is None:
        df = pd.DataFrame()

    df = pd.DataFrame(df).copy()

    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df = df.drop(
        columns=[
            "delete",
            "color_name",
        ],
        errors="ignore",
    )

    if df.empty:

        df["duration"] = pd.Series(
            dtype="float"
        )

        df["status"] = pd.Series(
            dtype="str"
        )

        return df

    # --------------------------------------------------------
    # FECHAS
    # --------------------------------------------------------

    df["start_date"] = pd.to_datetime(
        df["start_date"],
        errors="coerce",
    )

    df["end_date"] = pd.to_datetime(
        df["end_date"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # AVANCE
    # --------------------------------------------------------

    df["progress"] = pd.to_numeric(
        df["progress"],
        errors="coerce",
    ).fillna(0)

    df["progress"] = df["progress"].clip(
        lower=0,
        upper=100,
    )

    # --------------------------------------------------------
    # HP
    # --------------------------------------------------------

    df["capacity_hp"] = pd.to_numeric(
        df["capacity_hp"],
        errors="coerce",
    ).fillna(0)

    df["capacity_hp"] = (
        df["capacity_hp"]
        .round()
        .astype(int)
    )

    # --------------------------------------------------------
    # CRÍTICA
    # --------------------------------------------------------

    df["critical"] = (
        df["critical"]
        .fillna(False)
        .astype(bool)
    )

    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    def get_activity_color(
        row: pd.Series,
    ) -> str:

        activity = str(
            row.get(
                "activity_type",
                "",
            )
            or ""
        ).strip()

        current_color = row.get(
            "color"
        )

        fallback = COLORS.get(
            activity,
            DEFAULT_COLOR,
        )

        if (
            pd.notna(current_color)
            and str(current_color).strip()
        ):
            return validate_hex_color(
                current_color,
                fallback,
            )

        return fallback

    df["color"] = df.apply(
        get_activity_color,
        axis=1,
    )

    # --------------------------------------------------------
    # DURACIÓN
    # --------------------------------------------------------

    df["duration"] = (
        df["end_date"]
        - df["start_date"]
    ).dt.days + 1

    # --------------------------------------------------------
    # ESTADO
    # --------------------------------------------------------

    today = pd.Timestamp.today().normalize()

    def calculate_status(
        row: pd.Series,
    ) -> str:

        progress = float(
            row.get(
                "progress",
                0,
            )
            or 0
        )

        end_date = row.get(
            "end_date"
        )

        if progress >= 100:
            return "Finalizada"

        if (
            pd.notna(end_date)
            and end_date < today
        ):
            return "Retrasada"

        if progress > 0:
            return "En ejecución"

        return "Pendiente"

    df["status"] = df.apply(
        calculate_status,
        axis=1,
    )

    return df


# ============================================================
# SESSION STATE
# ============================================================

def initialize() -> None:

    if "project_data" not in st.session_state:
        st.session_state.project_data = load_project()

    if "activities" not in st.session_state:

        activities = (
            st.session_state
            .project_data
            .get(
                "activities",
                [],
            )
        )

        st.session_state.activities = normalize(
            pd.DataFrame(
                activities
            )
        )


# ============================================================
# DIAGRAMA DE GANTT
# ============================================================

def build_gantt(
    df: pd.DataFrame,
    start_year: int,
    years_to_show: int = 1,
) -> go.Figure:

    fig = go.Figure()

    years_to_show = max(
        1,
        min(
            int(years_to_show),
            3,
        ),
    )

    # ========================================================
    # TAMAÑOS ADAPTATIVOS
    # ========================================================

    if years_to_show == 1:

        year_font_size = 17
        quarter_font_size = 15
        month_font_size = 12
        week_font_size = 10
        bar_font_size = 11

    elif years_to_show == 2:

        year_font_size = 17
        quarter_font_size = 12
        month_font_size = 10
        week_font_size = 9
        bar_font_size = 10

    else:

        year_font_size = 16
        quarter_font_size = 11
        month_font_size = 8
        week_font_size = 7
        bar_font_size = 9

    # ========================================================
    # RANGO TEMPORAL
    # ========================================================

    start = pd.Timestamp(
        year=start_year,
        month=1,
        day=1,
    )

    end = pd.Timestamp(
        year=start_year + years_to_show,
        month=1,
        day=1,
    )

    display_end = (
        end
        - pd.Timedelta(days=1)
    )

    if df.empty:

        fig.update_layout(
            height=500,
            paper_bgcolor="#F4F7FB",
            plot_bgcolor="white",
        )

        fig.add_annotation(
            text="No hay actividades para mostrar",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                size=18,
                color="#667085",
            ),
        )

        return fig

    df = normalize(df)

    # ========================================================
    # ORDEN DE EQUIPOS
    # ========================================================

    rig_order = list(
        dict.fromkeys(
            df["rig"]
            .dropna()
            .astype(str)
            .tolist()
        )
    )

    y_map = {}

    tickvals = []
    ticktext = []

    current_y = 0.0

    # ========================================================
    # FILAS PLAN / REAL
    # ========================================================

    for rig in rig_order:

        rig_rows = df[
            df["rig"].astype(str)
            == rig
        ]

        if rig_rows.empty:
            capacity_hp = 0
        else:
            capacity_hp = int(
                rig_rows[
                    "capacity_hp"
                ].iloc[0]
            )

        y_map[
            (
                rig,
                "Plan",
            )
        ] = current_y

        y_map[
            (
                rig,
                "Real",
            )
        ] = current_y + 1

        tickvals.extend(
            [
                current_y,
                current_y + 1,
            ]
        )

        ticktext.extend(
            [
                (
                    f"<b>{rig}</b><br>"
                    f"{capacity_hp} HP · "
                    "<span style='color:#0047BA'>"
                    "<b>P</b></span>"
                ),
                (
                    f"<b>{rig}</b><br>"
                    f"{capacity_hp} HP · "
                    "<span style='color:#C00000'>"
                    "<b>R</b></span>"
                ),
            ]
        )

        current_y += 2.5

    # ========================================================
    # ACTIVIDADES
    # ========================================================

    sorted_df = df.sort_values(
        [
            "rig",
            "schedule_type",
            "start_date",
        ]
    )

    for _, row in sorted_df.iterrows():

        start_date = row.get(
            "start_date"
        )

        end_date = row.get(
            "end_date"
        )

        rig = str(
            row.get(
                "rig",
                "",
            )
        )

        schedule_type = str(
            row.get(
                "schedule_type",
                "",
            )
        )

        if (
            pd.isna(start_date)
            or pd.isna(end_date)
        ):
            continue

        if end_date < start_date:
            continue

        # Actividad completamente fuera del periodo
        if (
            end_date < start
            or start_date > display_end
        ):
            continue

        y_value = y_map.get(
            (
                rig,
                schedule_type,
            )
        )

        if y_value is None:
            continue

        # ----------------------------------------------------
        # RECORTE VISUAL
        # ----------------------------------------------------

        visible_start = max(
            start_date,
            start,
        )

        visible_end = min(
            end_date,
            display_end,
        )

        # ----------------------------------------------------
        # COLOR
        # ----------------------------------------------------

        activity_type = str(
            row.get(
                "activity_type",
                "",
            )
            or ""
        )

        color = validate_hex_color(
            row.get(
                "color",
                "",
            ),
            COLORS.get(
                activity_type,
                DEFAULT_COLOR,
            ),
        )

        # ----------------------------------------------------
        # ETIQUETA
        # ----------------------------------------------------

        label = str(
            row.get(
                "label",
                "",
            )
            or row.get(
                "well",
                "",
            )
            or activity_type
            or "Actividad"
        )

        # ----------------------------------------------------
        # BARRA
        # ----------------------------------------------------

        fig.add_shape(
            type="rect",
            x0=visible_start,
            x1=visible_end,
            y0=y_value - 0.38,
            y1=y_value + 0.38,
            line=dict(
                color="#6B6B6B",
                width=0.7,
            ),
            fillcolor=color,
            layer="below",
        )

        midpoint = (
            visible_start
            + (
                visible_end
                - visible_start
            ) / 2
        )

        duration = row.get(
            "duration",
            0,
        )

        if pd.isna(duration):
            duration = 0

        progress = row.get(
            "progress",
            0,
        )

        status = row.get(
            "status",
            "",
        )

        well = row.get(
            "well",
            "",
        )

        # ----------------------------------------------------
        # TEXTO DE LA BARRA
        # ----------------------------------------------------

        fig.add_annotation(
            x=midpoint,
            y=y_value,
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(
                size=bar_font_size,
                color="#111111",
            ),
            xanchor="center",
            yanchor="middle",
            hovertext=(
                f"<b>{label}</b><br>"
                f"Equipo: {rig}<br>"
                f"Tipo: {schedule_type}<br>"
                f"Pozo: {well}<br>"
                f"Actividad: {activity_type}<br>"
                f"Inicio: {start_date:%d/%m/%Y}<br>"
                f"Fin: {end_date:%d/%m/%Y}<br>"
                f"Duración: {int(duration)} días<br>"
                f"Avance: {float(progress):.0f}%<br>"
                f"Estado: {status}"
            ),
        )

    # ========================================================
    # ENCABEZADO
    # IMPORTANTE:
    # Las líneas siguientes SOLO se dibujan en el encabezado.
    # y0/y1 usan coordenadas "paper".
    # ========================================================

    header_bottom = 1.01
    week_top = 1.055
    month_top = 1.105
    quarter_top = 1.165
    year_top = 1.235

    # ========================================================
    # AÑOS
    # ========================================================

    for current_year in range(
        start_year,
        start_year + years_to_show,
    ):

        year_start = pd.Timestamp(
            current_year,
            1,
            1,
        )

        year_end = pd.Timestamp(
            current_year + 1,
            1,
            1,
        )

        year_midpoint = (
            year_start
            + (
                year_end
                - year_start
            ) / 2
        )

        # Separador SOLO en encabezado
        fig.add_shape(
            type="line",
            x0=year_start,
            x1=year_start,
            y0=header_bottom,
            y1=year_top,
            xref="x",
            yref="paper",
            line=dict(
                color="#17365D",
                width=2.5,
            ),
        )

        fig.add_annotation(
            x=year_midpoint,
            y=1.215,
            xref="x",
            yref="paper",
            text=f"<b>{current_year}</b>",
            showarrow=False,
            font=dict(
                size=year_font_size,
                color="white",
            ),
            bgcolor="#1F4E78",
            bordercolor="#17365D",
            borderwidth=1,
            borderpad=4,
        )

    # Separador final de años
    fig.add_shape(
        type="line",
        x0=end,
        x1=end,
        y0=header_bottom,
        y1=year_top,
        xref="x",
        yref="paper",
        line=dict(
            color="#17365D",
            width=2.5,
        ),
    )

    # ========================================================
    # TRIMESTRES
    # ========================================================

    quarter_months = [
        ("Q1", 1, 4),
        ("Q2", 4, 7),
        ("Q3", 7, 10),
        ("Q4", 10, 13),
    ]

    for current_year in range(
        start_year,
        start_year + years_to_show,
    ):

        for (
            quarter_name,
            start_month,
            end_month,
        ) in quarter_months:

            quarter_start = pd.Timestamp(
                current_year,
                start_month,
                1,
            )

            if end_month == 13:

                quarter_end = pd.Timestamp(
                    current_year + 1,
                    1,
                    1,
                )

            else:

                quarter_end = pd.Timestamp(
                    current_year,
                    end_month,
                    1,
                )

            quarter_midpoint = (
                quarter_start
                + (
                    quarter_end
                    - quarter_start
                ) / 2
            )

            # Línea SOLO en encabezado
            fig.add_shape(
                type="line",
                x0=quarter_start,
                x1=quarter_start,
                y0=header_bottom,
                y1=quarter_top,
                xref="x",
                yref="paper",
                line=dict(
                    color="#1F4E78",
                    width=1.8,
                ),
            )

            fig.add_annotation(
                x=quarter_midpoint,
                y=1.145,
                xref="x",
                yref="paper",
                text=f"<b>{quarter_name}</b>",
                showarrow=False,
                font=dict(
                    size=quarter_font_size,
                    color="#1F4E78",
                ),
            )

    # ========================================================
    # MESES
    # ========================================================

    month_starts = pd.date_range(
        start=start,
        end=display_end,
        freq="MS",
    )

    month_names_map = {
        1: "Ene",
        2: "Feb",
        3: "Mar",
        4: "Abr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dic",
    }

    for month_start in month_starts:

        next_month = (
            month_start
            + pd.offsets.MonthBegin(1)
        )

        month_midpoint = (
            month_start
            + (
                next_month
                - month_start
            ) / 2
        )

        # Separador de mes SOLO en encabezado
        fig.add_shape(
            type="line",
            x0=month_start,
            x1=month_start,
            y0=header_bottom,
            y1=month_top,
            xref="x",
            yref="paper",
            line=dict(
                color="rgba(31,78,121,0.60)",
                width=1,
            ),
        )

        fig.add_annotation(
            x=month_midpoint,
            y=1.087,
            xref="x",
            yref="paper",
            text=(
                f"<b>"
                f"{month_names_map[month_start.month]}"
                f"</b>"
            ),
            showarrow=False,
            font=dict(
                size=month_font_size,
                color="#17365D",
            ),
        )

    # ========================================================
    # SEMANAS
    # ========================================================

    for month_start in month_starts:

        next_month = (
            month_start
            + pd.offsets.MonthBegin(1)
        )

        week_start = month_start
        week_number = 1

        while week_start < next_month:

            week_end = min(
                week_start
                + pd.Timedelta(days=7),
                next_month,
            )

            week_midpoint = (
                week_start
                + (
                    week_end
                    - week_start
                ) / 2
            )

            # Separador de semana SOLO en encabezado
            fig.add_shape(
                type="line",
                x0=week_start,
                x1=week_start,
                y0=header_bottom,
                y1=week_top,
                xref="x",
                yref="paper",
                line=dict(
                    color="rgba(90,105,120,0.45)",
                    width=0.5,
                ),
            )

            fig.add_annotation(
                x=week_midpoint,
                y=1.033,
                xref="x",
                yref="paper",
                text=f"S{week_number}",
                showarrow=False,
                font=dict(
                    size=week_font_size,
                    color="#5B6573",
                ),
            )

            week_start = week_end
            week_number += 1

    # ========================================================
    # LÍNEAS HORIZONTALES DEL ENCABEZADO
    # ========================================================

    for header_y in [
        header_bottom,
        week_top,
        month_top,
        quarter_top,
    ]:

        fig.add_shape(
            type="line",
            x0=start,
            x1=end,
            y0=header_y,
            y1=header_y,
            xref="x",
            yref="paper",
            line=dict(
                color="rgba(31,78,121,0.35)",
                width=1,
            ),
        )

    # ========================================================
    # FECHA ACTUAL
    # Esta sí atraviesa el Gantt
    # ========================================================

    today = (
        pd.Timestamp
        .today()
        .normalize()
    )

    if start <= today <= display_end:

        fig.add_vline(
            x=today,
            line_width=2,
            line_dash="dash",
            line_color="#D13438",
        )

        fig.add_annotation(
            x=today,
            y=1.005,
            xref="x",
            yref="paper",
            text="<b>HOY</b>",
            showarrow=False,
            font=dict(
                size=10,
                color="#D13438",
            ),
        )

    # ========================================================
    # SEPARADORES HORIZONTALES ENTRE EQUIPOS
    # ========================================================

    for rig in rig_order[:-1]:

        separator = (
            y_map[
                (
                    rig,
                    "Real",
                )
            ]
            + 0.75
        )

        fig.add_hline(
            y=separator,
            line_width=2,
            line_color="#E7ECF2",
        )

    # ========================================================
    # ALTURA DINÁMICA
    # ========================================================

    number_of_rigs = len(
        rig_order
    )

    chart_height = max(
        600,
        number_of_rigs * 130,
    )

    last_y_position = (
        max(tickvals)
        if tickvals
        else 0
    )

    vertical_limit = (
        last_y_position
        + 0.9
    )

    # ========================================================
    # LAYOUT
    # ========================================================

    fig.update_layout(
        height=chart_height,

        margin=dict(
            l=10,
            r=10,
            t=175,
            b=20,
        ),

        paper_bgcolor="#F4F7FB",
        plot_bgcolor="white",

        showlegend=False,

        font=dict(
            family="Segoe UI, Arial, sans-serif",
            color="#252423",
        ),

        xaxis=dict(
            type="date",

            range=[
                start,
                end,
            ],

            side="top",

            showticklabels=False,

            # IMPORTANTE:
            # Sin cuadrícula vertical dentro del Gantt
            showgrid=False,

            zeroline=False,

            fixedrange=False,
        ),

        yaxis=dict(
            tickmode="array",

            tickvals=tickvals,

            ticktext=ticktext,

            range=[
                vertical_limit,
                -0.8,
            ],

            autorange=False,

            showgrid=False,

            zeroline=False,

            fixedrange=True,

            tickfont=dict(
                size=12,
            ),
        ),

        dragmode="pan",
    )

    return fig


# ============================================================
# EXPORTAR JSON
# ============================================================

def export_json(
    project: dict,
    df: pd.DataFrame,
) -> str:

    export_df = normalize(
        df
    ).copy()

    export_df["start_date"] = (
        pd.to_datetime(
            export_df["start_date"],
            errors="coerce",
        )
        .dt.strftime(
            "%Y-%m-%d"
        )
    )

    export_df["end_date"] = (
        pd.to_datetime(
            export_df["end_date"],
            errors="coerce",
        )
        .dt.strftime(
            "%Y-%m-%d"
        )
    )

    export_df = export_df.drop(
        columns=[
            "duration",
            "status",
            "delete",
            "color_name",
        ],
        errors="ignore",
    )

    export_df = export_df.where(
        pd.notna(
            export_df
        ),
        None,
    )

    payload = {
        "project": project,
        "activities": (
            export_df
            .to_dict(
                orient="records"
            )
        ),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# INICIAR APP
# ============================================================

load_css()
initialize()


project = (
    st.session_state
    .project_data
    .get(
        "project",
        {},
    )
)


df = normalize(
    st.session_state.activities
)


st.session_state.activities = df


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "<div class='brand'>GSM BRONCO</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Planeación y seguimiento de pozos"
    )

    page = st.radio(
        "Navegación",
        [
            "Dashboard ejecutivo",
            "Actividades",
            "Proyecto y archivos",
        ],
    )

    st.divider()

    st.write(
        f"**{project.get('name', 'Proyecto sin nombre')}**"
    )

    st.caption(
        f"Código: {project.get('code', 'N/D')}"
    )

    st.caption(
        f"Responsable: {project.get('manager', 'N/D')}"
    )

    st.caption(
        f"Estado: {project.get('status', 'N/D')}"
    )


# ============================================================
# ENCABEZADO GENERAL
# ============================================================

project_name = project.get(
    "name",
    "Programa Integral de Equipos 2026",
)

project_status = project.get(
    "status",
    "En ejecución",
)


st.markdown(
    f"""
<div class="header-card">
    <div>
        <div class="title">PROYECTO INTEGRAL FINANCIADO CAMPO IXACHI</div>
        <div class="subtitle">{project_name}</div>
    </div>
    <div class="pill">{project_status}</div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard ejecutivo":

    st.markdown(
        "## Cronograma ejecutivo Plan vs. Real"
    )

    col_year, col_period, col_rigs = st.columns(
        [
            1,
            1,
            3,
        ]
    )

    default_year = int(
        project.get(
            "year",
            2026,
        )
    )

    available_years = [
        2025,
        2026,
        2027,
        2028,
        2029,
        2030,
    ]

    try:

        year_index = (
            available_years
            .index(
                default_year
            )
        )

    except ValueError:
        year_index = 1

    # --------------------------------------------------------
    # AÑO INICIAL
    # --------------------------------------------------------

    year = col_year.selectbox(
        "Año inicial",
        available_years,
        index=year_index,
    )

    # --------------------------------------------------------
    # PERIODO
    # --------------------------------------------------------

    years_to_show = col_period.selectbox(
        "Periodo",
        options=[
            1,
            2,
            3,
        ],
        index=0,
        format_func=lambda value: (
            f"{value} año"
            if value == 1
            else f"{value} años"
        ),
    )

    # --------------------------------------------------------
    # EQUIPOS
    # --------------------------------------------------------

    rigs = sorted(
        df["rig"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_rigs = col_rigs.multiselect(
        "Equipos",
        options=rigs,
        default=rigs,
    )

    filtered = df[
        df["rig"]
        .astype(str)
        .isin(
            selected_rigs
        )
    ].copy()

    # --------------------------------------------------------
    # GANTT
    # --------------------------------------------------------

    gantt_figure = build_gantt(
        filtered,
        year,
        years_to_show,
    )

    st.plotly_chart(
        gantt_figure,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": True,
            "responsive": True,
        },
    )


# ============================================================
# ACTIVIDADES
# ============================================================

elif page == "Actividades":

    st.markdown(
        "## Tabla editable de actividades"
    )

    st.caption(
        "Puedes agregar, modificar o eliminar actividades. "
        "Los datos que gestiona esta tabla son directamente "
        "reflejados en el diagrama de Gantt."
    )

    # ========================================================
    # LEYENDA DE COLORES
    # ========================================================

    color_legend_html = """
<div style="background:white;border:1px solid #DCE3EC;border-radius:10px;padding:14px 16px;margin-top:8px;margin-bottom:16px;box-shadow:0 2px 6px rgba(15,39,71,0.04);">
<div style="font-weight:700;color:#17365D;margin-bottom:10px;">Referencia de colores</div>
<div style="display:flex;flex-wrap:wrap;gap:14px 22px;align-items:center;">

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#FFD966;border:1px solid #999;border-radius:3px;"></span>
Amarillo
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#FFC000;border:1px solid #999;border-radius:3px;"></span>
Amarillo intenso
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#A9D18E;border:1px solid #999;border-radius:3px;"></span>
Verde claro
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#70AD47;border:1px solid #999;border-radius:3px;"></span>
Verde
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#00B050;border:1px solid #999;border-radius:3px;"></span>
Verde intenso
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#5B9BD5;border:1px solid #999;border-radius:3px;"></span>
Azul
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#4472C4;border:1px solid #999;border-radius:3px;"></span>
Azul oscuro
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#D9D9D9;border:1px solid #999;border-radius:3px;"></span>
Gris
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#A5A5A5;border:1px solid #999;border-radius:3px;"></span>
Gris oscuro
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#ED7D31;border:1px solid #999;border-radius:3px;"></span>
Naranja
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#7030A0;border:1px solid #999;border-radius:3px;"></span>
Morado
</div>

<div style="display:flex;align-items:center;gap:6px;">
<span style="display:inline-block;width:18px;height:18px;background:#C00000;border:1px solid #999;border-radius:3px;"></span>
Rojo
</div>

</div>
</div>
"""

    st.markdown(
        color_legend_html,
        unsafe_allow_html=True,
    )

    # ========================================================
    # PREPARAR TABLA
    # ========================================================

    editable = df.copy()

    editable["start_date"] = (
        pd.to_datetime(
            editable["start_date"],
            errors="coerce",
        )
        .dt.date
    )

    editable["end_date"] = (
        pd.to_datetime(
            editable["end_date"],
            errors="coerce",
        )
        .dt.date
    )

    editable["delete"] = False

    editable["color_name"] = (
        editable["color"]
        .astype(str)
        .str.upper()
        .map(
            HEX_TO_COLOR_NAME
        )
        .fillna(
            "🟦 Azul"
        )
    )

    # ========================================================
    # EDITOR
    # ========================================================

    edited = st.data_editor(
        editable,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",

        column_order=[
            "delete",
            "id",
            "rig",
            "capacity_hp",
            "schedule_type",
            "well",
            "activity_type",
            "label",
            "color_name",
            "start_date",
            "end_date",
            "duration",
            "progress",
            "status",
            "critical",
        ],

        column_config={

            "delete": (
                st.column_config.CheckboxColumn(
                    "Eliminar",
                    help=(
                        "Marca esta casilla "
                        "para eliminar la actividad"
                    ),
                    default=False,
                )
            ),

            "id": (
                st.column_config.NumberColumn(
                    "ID",
                    min_value=1,
                    step=1,
                )
            ),

            "rig": (
                st.column_config.TextColumn(
                    "Equipo",
                    help="Ejemplo: RIG-90",
                )
            ),

            "capacity_hp": (
                st.column_config.NumberColumn(
                    "HP",
                    min_value=0,
                    step=100,
                )
            ),

            "schedule_type": (
                st.column_config.SelectboxColumn(
                    "Plan/Real",
                    options=[
                        "Plan",
                        "Real",
                    ],
                    required=True,
                )
            ),

            "well": (
                st.column_config.TextColumn(
                    "Pozo",
                    help="Ejemplo: IXACHI-64",
                )
            ),

            "activity_type": (
                st.column_config.TextColumn(
                    "Actividad",
                    help=(
                        "Escribe libremente "
                        "el nombre de la actividad"
                    ),
                    max_chars=100,
                )
            ),

            "label": (
                st.column_config.TextColumn(
                    "Texto de barra",
                    help=(
                        "Texto que aparecerá "
                        "dentro de la barra del Gantt"
                    ),
                    max_chars=150,
                )
            ),

            "color_name": (
                st.column_config.SelectboxColumn(
                    "Color",
                    help=(
                        "Selecciona el color "
                        "de la barra del Gantt"
                    ),
                    options=list(
                        COLOR_OPTIONS.keys()
                    ),
                    required=True,
                )
            ),

            "start_date": (
                st.column_config.DateColumn(
                    "Inicio",
                    format="DD/MM/YYYY",
                )
            ),

            "end_date": (
                st.column_config.DateColumn(
                    "Fin",
                    format="DD/MM/YYYY",
                )
            ),

            "duration": (
                st.column_config.NumberColumn(
                    "Duración",
                    disabled=True,
                )
            ),

            "progress": (
                st.column_config.ProgressColumn(
                    "Avance",
                    min_value=0,
                    max_value=100,
                    format="%d%%",
                )
            ),

            "status": (
                st.column_config.TextColumn(
                    "Estado",
                    disabled=True,
                )
            ),

            "critical": (
                st.column_config.CheckboxColumn(
                    "Crítica"
                )
            ),
        },

        disabled=[
            "duration",
            "status",
        ],

        key="activities_editor",
    )

    # ========================================================
    # BOTÓN GUARDAR
    # ========================================================

    col_save, col_help = st.columns(
        [
            1,
            3,
        ]
    )

    save_button = col_save.button(
        "Guardar cambios",
        type="primary",
        use_container_width=True,
    )

    # ========================================================
    # GUARDAR CAMBIOS
    # ========================================================

    if save_button:

        updated_df = pd.DataFrame(
            edited
        ).copy()

        # ----------------------------------------------------
        # COLOR
        # ----------------------------------------------------

        if "color_name" in updated_df.columns:

            updated_df["color"] = (
                updated_df[
                    "color_name"
                ]
                .map(
                    COLOR_OPTIONS
                )
                .fillna(
                    DEFAULT_COLOR
                )
            )

        updated_df = updated_df.drop(
            columns=[
                "color_name",
            ],
            errors="ignore",
        )

        # ----------------------------------------------------
        # ELIMINAR
        # ----------------------------------------------------

        deleted_count = 0

        if "delete" in updated_df.columns:

            delete_mask = (
                updated_df[
                    "delete"
                ]
                .fillna(False)
                .astype(bool)
            )

            deleted_count = int(
                delete_mask.sum()
            )

            updated_df = updated_df[
                ~delete_mask
            ].copy()

            updated_df = updated_df.drop(
                columns=[
                    "delete"
                ],
                errors="ignore",
            )

        # ----------------------------------------------------
        # FILAS VACÍAS
        # ----------------------------------------------------

        important_columns = [
            "rig",
            "well",
            "activity_type",
            "label",
            "start_date",
            "end_date",
        ]

        existing_columns = [
            column
            for column in important_columns
            if column in updated_df.columns
        ]

        if existing_columns:

            updated_df = updated_df.dropna(
                subset=existing_columns,
                how="all",
            )

        # ----------------------------------------------------
        # NORMALIZAR
        # ----------------------------------------------------

        updated_df = normalize(
            updated_df
        )

        st.session_state.activities = (
            updated_df
        )

        # ----------------------------------------------------
        # SINCRONIZAR PROJECT DATA
        # ----------------------------------------------------

        export_copy = (
            updated_df
            .copy()
        )

        export_copy["start_date"] = (
            export_copy["start_date"]
            .dt.strftime(
                "%Y-%m-%d"
            )
        )

        export_copy["end_date"] = (
            export_copy["end_date"]
            .dt.strftime(
                "%Y-%m-%d"
            )
        )

        export_copy = export_copy.drop(
            columns=[
                "duration",
                "status",
                "delete",
                "color_name",
            ],
            errors="ignore",
        )

        st.session_state[
            "project_data"
        ][
            "activities"
        ] = export_copy.to_dict(
            orient="records"
        )

        if deleted_count > 0:

            st.success(
                f"Se eliminaron {deleted_count} actividad(es) "
                "y se guardaron los cambios."
            )

        else:

            st.success(
                "Cambios guardados correctamente."
            )

        st.rerun()


# ============================================================
# PROYECTO Y ARCHIVOS
# ============================================================

elif page == "Proyecto y archivos":

    st.markdown(
        "## Proyecto y archivos"
    )

    # ========================================================
    # INFORMACIÓN DEL PROYECTO
    # ========================================================

    with st.form(
        "project_form"
    ):

        project_name_input = st.text_input(
            "Nombre del proyecto",
            value=project.get(
                "name",
                "",
            ),
        )

        project_code_input = st.text_input(
            "Código",
            value=project.get(
                "code",
                "",
            ),
        )

        project_manager_input = st.text_input(
            "Responsable",
            value=project.get(
                "manager",
                "",
            ),
        )

        status_options = [
            "En planificación",
            "En ejecución",
            "Suspendido",
            "Finalizado",
        ]

        current_status = project.get(
            "status",
            "En planificación",
        )

        try:

            status_index = (
                status_options
                .index(
                    current_status
                )
            )

        except ValueError:
            status_index = 0

        project_status_input = st.selectbox(
            "Estado",
            options=status_options,
            index=status_index,
        )

        project_year_input = st.number_input(
            "Año de referencia",
            min_value=2020,
            max_value=2100,
            value=int(
                project.get(
                    "year",
                    2026,
                )
            ),
            step=1,
        )

        update_project_button = (
            st.form_submit_button(
                "Actualizar proyecto",
                type="primary",
            )
        )

    if update_project_button:

        updated_project = {
            "name": project_name_input,
            "code": project_code_input,
            "manager": project_manager_input,
            "status": project_status_input,
            "year": int(
                project_year_input
            ),
        }

        st.session_state[
            "project_data"
        ][
            "project"
        ] = updated_project

        st.success(
            "Información del proyecto actualizada."
        )

        st.rerun()

    # ========================================================
    # ABRIR JSON
    # ========================================================

    st.divider()

    st.markdown(
        "### Abrir proyecto JSON"
    )

    uploaded = st.file_uploader(
        "Selecciona un archivo JSON de GSM BRONCO",
        type=[
            "json"
        ],
    )

    if uploaded is not None:

        try:

            loaded = json.load(
                uploaded
            )

            if "project" not in loaded:

                raise ValueError(
                    "El archivo no contiene "
                    "la sección 'project'."
                )

            if "activities" not in loaded:

                raise ValueError(
                    "El archivo no contiene "
                    "la sección 'activities'."
                )

            st.session_state[
                "project_data"
            ] = loaded

            st.session_state[
                "activities"
            ] = normalize(
                pd.DataFrame(
                    loaded[
                        "activities"
                    ]
                )
            )

            st.success(
                "Proyecto cargado correctamente."
            )

            st.rerun()

        except json.JSONDecodeError:

            st.error(
                "El archivo seleccionado "
                "no es un JSON válido."
            )

        except Exception as error:

            st.error(
                "No fue posible cargar "
                f"el archivo: {error}"
            )

    # ========================================================
    # DESCARGAR JSON
    # ========================================================

    st.divider()

    st.markdown(
        "### Descargar proyecto"
    )

    current_project = (
        st.session_state[
            "project_data"
        ]
        .get(
            "project",
            {},
        )
    )

    current_activities = (
        st.session_state[
            "activities"
        ]
    )

    json_data = export_json(
        current_project,
        current_activities,
    )

    filename_code = (
        current_project
        .get(
            "code",
            "gsm_bronco",
        )
    )

    st.download_button(
        label="Descargar proyecto actualizado",
        data=json_data,
        file_name=f"{filename_code}.json",
        mime="application/json",
        type="primary",
    )