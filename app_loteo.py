import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import pytz
from ortools.sat.python import cp_model
from io import BytesIO

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Loteador Óptimo | Elcatex",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── ELCATEX THEME ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 12px; }

  /* Main background */
  .stApp { background-color: #f4f6f9; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #003876 0%, #0057a8 60%, #0080c9 100%);
  }
  [data-testid="stSidebar"] * { color: #ffffff !important; font-size: 11.5px !important; }
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stNumberInput label,
  [data-testid="stSidebar"] .stTextInput label { color: #cce4ff !important; font-weight: 500 !important; }

  /* Headers */
  h1 { color: #003876 !important; font-size: 20px !important; font-weight: 700 !important; }
  h2 { color: #0057a8 !important; font-size: 15px !important; font-weight: 600 !important; }
  h3 { color: #003876 !important; font-size: 13px !important; font-weight: 600 !important; }

  /* Cards */
  .elc-card {
    background: white;
    border-radius: 8px;
    padding: 16px 20px;
    border-left: 4px solid #0057a8;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    margin-bottom: 12px;
  }
  .elc-card-red { border-left-color: #c0392b; }
  .elc-card-green { border-left-color: #1a7a4a; }
  .elc-card-gray { border-left-color: #7f8c8d; }

  /* Metric boxes */
  .metric-box {
    background: white;
    border-radius: 8px;
    padding: 14px 16px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }
  .metric-val { font-size: 22px; font-weight: 700; color: #003876; }
  .metric-lbl { font-size: 10px; color: #7f8c8d; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(135deg, #0057a8, #003876);
    color: white !important;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 20px;
    transition: all 0.2s;
  }
  .stButton > button:hover { background: linear-gradient(135deg, #0080c9, #0057a8); box-shadow: 0 3px 10px rgba(0,87,168,0.4); }

  /* DataFrames */
  .stDataFrame { border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { background: white; border-radius: 8px 8px 0 0; gap: 2px; padding: 4px; }
  .stTabs [data-baseweb="tab"] { font-size: 11.5px; font-weight: 600; color: #7f8c8d; border-radius: 6px; }
  .stTabs [aria-selected="true"] { background: #0057a8 !important; color: white !important; }

  /* Toggle label */
  .stCheckbox label { font-size: 11.5px !important; }

  /* Divider */
  hr { border-color: #e8ecf0; margin: 10px 0; }

  /* Badge */
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-green { background: #d1fae5; color: #065f46; }
  .badge-orange { background: #ffedd5; color: #9a3412; }
  .badge-gray { background: #f1f5f9; color: #475569; }

  /* Logo area */
  .logo-header {
    background: linear-gradient(135deg, #003876, #0057a8);
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 16px;
    display: flex; align-items: center; gap: 12px;
  }
  .logo-title { color: white; font-size: 18px; font-weight: 700; margin: 0; }
  .logo-sub { color: #cce4ff; font-size: 10px; margin: 0; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ──────────────────────────────────────────────────────────────────
PROFILES_FILE = "elcatex_profiles.json"
DIAS_SEMANA = 7

DEFAULT_CAPACIDADES = [
    {"CATEGORIA": "A-4000", "MINIMO": 3900, "MAXIMO": 4000, "LOTES": 5,  "MIX": "DYE",    "SEMANAS": 4, "MIN_ANCHO": 1, "MAX_ANCHO": 4, "CTDMAXANCHOS": 4, "TIPO_TEJIDO": "FLEECE", "ACTIVO": True},
    {"CATEGORIA": "B-3300", "MINIMO": 3000, "MAXIMO": 3300, "LOTES": 6,  "MIX": "DYE",    "SEMANAS": 4, "MIN_ANCHO": 1, "MAX_ANCHO": 4, "CTDMAXANCHOS": 4, "TIPO_TEJIDO": "TODOS",  "ACTIVO": True},
    {"CATEGORIA": "C-2600", "MINIMO": 2500, "MAXIMO": 2600, "LOTES": 29, "MIX": "DYE",    "SEMANAS": 4, "MIN_ANCHO": 1, "MAX_ANCHO": 4, "CTDMAXANCHOS": 3, "TIPO_TEJIDO": "TODOS",  "ACTIVO": True},
    {"CATEGORIA": "D-2200", "MINIMO": 2000, "MAXIMO": 2200, "LOTES": 17, "MIX": "DYE",    "SEMANAS": 4, "MIN_ANCHO": 1, "MAX_ANCHO": 4, "CTDMAXANCHOS": 3, "TIPO_TEJIDO": "TODOS",  "ACTIVO": True},
    {"CATEGORIA": "E-1100", "MINIMO": 1000, "MAXIMO": 1100, "LOTES": 25, "MIX": "DYE",    "SEMANAS": 4, "MIN_ANCHO": 1, "MAX_ANCHO": 4, "CTDMAXANCHOS": 2, "TIPO_TEJIDO": "JERSEY", "ACTIVO": True},
    {"CATEGORIA": "F-2200", "MINIMO": 2000, "MAXIMO": 2200, "LOTES": 21, "MIX": "BLEACH", "SEMANAS": 4, "MIN_ANCHO": 1, "MAX_ANCHO": 4, "CTDMAXANCHOS": 3, "TIPO_TEJIDO": "TODOS",  "ACTIVO": True},
    {"CATEGORIA": "G-1100", "MINIMO": 1000, "MAXIMO": 1100, "LOTES": 4,  "MIX": "BLEACH", "SEMANAS": 4, "MIN_ANCHO": 1, "MAX_ANCHO": 4, "CTDMAXANCHOS": 2, "TIPO_TEJIDO": "TODOS",  "ACTIVO": True},
]

DEFAULT_CONFIG = {
    "MAX_ITEMS": 8,
    "SOLVER_TIMEOUT": 5,
    "COMBINACION_PRIORIDAD": [["VENCIDOS", "AHEAD"], ["AHEAD", "AHEAD2"], ["AHEAD2", "OTROS"]],
    "APPLY_RULES_BLEACH": False,
}

DEFAULT_RESTRICCIONES_ANCHO = [
    {"STYLE": "PC54Y",   "LIMITE_ANCHO": 18, "PRIORIDAD_1": 2600, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "ACTIVO": True},
    {"STYLE": "PC55LS",  "LIMITE_ANCHO": 18, "PRIORIDAD_1": 2600, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "ACTIVO": True},
    {"STYLE": "PC55Y",   "LIMITE_ANCHO": 18, "PRIORIDAD_1": 2600, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "ACTIVO": True},
    {"STYLE": "PC330Y",  "LIMITE_ANCHO": 18, "PRIORIDAD_1": 2200, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "ACTIVO": True},
    {"STYLE": "PC54-2",  "LIMITE_ANCHO": 18, "PRIORIDAD_1": 2600, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "ACTIVO": True},
]

DEFAULT_RESTRICCIONES_COLOR = [
    {"COLOR_R": "RESTRICCION", "PRIORIDAD_1": 2600, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "ACTIVO": True},
    {"COLOR_R": "NORMAL",      "PRIORIDAD_1": None, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "ACTIVO": True},
]

DEFAULT_RESTRICCIONES_FAMILIA = [
    {"FAMILIA": "PC68",    "PRIORIDAD_1": 2600, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "PRIORIDAD_4": None, "ACTIVO": True},
    {"FAMILIA": "PC850",   "PRIORIDAD_1": 2600, "PRIORIDAD_2": None, "PRIORIDAD_3": None, "PRIORIDAD_4": None, "ACTIVO": True},
    {"FAMILIA": "PC78/90", "PRIORIDAD_1": 4000, "PRIORIDAD_2": 2600, "PRIORIDAD_3": 3300, "PRIORIDAD_4": None, "ACTIVO": True},
]

DEFAULT_REGLAS_ANCHOS_COMBINADOS = []

# ─── PROFILE MANAGEMENT ─────────────────────────────────────────────────────────
def load_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            return json.load(f)
    return {}

def save_profiles(profiles):
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2, default=str)

def save_current_profile(name, capacidades, config, rest_ancho, rest_color, rest_familia, anchos_combinados):
    profiles = load_profiles()
    profiles[name] = {
        "capacidades": capacidades,
        "config": config,
        "rest_ancho": rest_ancho,
        "rest_color": rest_color,
        "rest_familia": rest_familia,
        "anchos_combinados": anchos_combinados,
        "saved_at": datetime.now().isoformat()
    }
    save_profiles(profiles)

def load_profile(name):
    profiles = load_profiles()
    return profiles.get(name, None)

# ─── DATA LOADING ────────────────────────────────────────────────────────────────
def build_join_from_data(df_raw):
    """Build the JOIN-equivalent DataFrame from the DATA sheet."""
    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.replace('\xa0', '', regex=True)

    needed = ['STYLE','COLOR','TELA.CUERPO','ANCHO.F.C','TOTAL','MIX','COLOR_R','FAMILIA','PRIORIDAD','TONO']
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.error(f"Columnas faltantes en DATA: {missing}")
        return None

    # Optional columns
    df['TIPO_TEJIDO'] = df.get('TIPO_TEJIDO', pd.Series(['TODOS']*len(df), index=df.index))
    df['PCT_CARGA']   = pd.to_numeric(df.get('PCT_CARGA', pd.Series([1.0]*len(df), index=df.index)), errors='coerce').fillna(1.0)

    df = df.rename(columns={
        'COLOR':       'COLOR_A',
        'TELA.CUERPO': 'ESTILO_C',
        'ANCHO.F.C':   'ANCHO',
        'TOTAL':       'LBS_C',
    })

    df['LBS_C']  = pd.to_numeric(df['LBS_C'], errors='coerce')
    df['ANCHO']  = pd.to_numeric(df['ANCHO'], errors='coerce')
    df['MIX']    = df['MIX'].str.upper().str.strip()
    df = df.dropna(subset=['LBS_C','ANCHO','COLOR_A','ESTILO_C']).reset_index(drop=True)

    # Build MIX_ANCHOS per COLOR_A+ESTILO_C group  → aggregated as set string
    df['MIX_ANCHOS'] = df['ANCHO'].astype(str)

    return df

@st.cache_data(show_spinner=False)
def read_excel_data(file_bytes):
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheets = xl.sheet_names
    if 'DATA' not in sheets:
        return None, "No se encontró la hoja DATA en el archivo."
    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name='DATA', header=2)
    return df_raw, None

# ─── LOTEADOR ────────────────────────────────────────────────────────────────────
def run_loteador(df, cap_row, max_items, solver_timeout, rest_ancho_df, rest_color_df, rest_familia_df):
    """Run OR-Tools loteador for a single category row."""
    min_lbs   = cap_row['MINIMO']
    max_lbs   = cap_row['MAXIMO']
    mix_tipo  = cap_row['MIX'].upper()
    tipo_tej  = cap_row['TIPO_TEJIDO'].upper()
    max_anchos = int(cap_row['CTDMAXANCHOS'])

    # Filter by MIX
    grupo = df[df['MIX'].str.upper() == mix_tipo].copy()

    # Filter by TIPO_TEJIDO
    if tipo_tej != 'TODOS':
        grupo = grupo[grupo['TIPO_TEJIDO'].str.upper().isin([tipo_tej, 'TODOS'])]

    # Apply RESTRICCIONES_ANCHO (overrides category for certain styles)
    rest_ancho_activas = rest_ancho_df[rest_ancho_df.get('ACTIVO', True) != False] if not rest_ancho_df.empty else rest_ancho_df

    def parse_anchos(x):
        return set(str(x).split("-"))

    def parse_telas(x):
        return set(str(x).split("-"))

    grupo['ANCHOS_SET'] = grupo['MIX_ANCHOS'].apply(parse_anchos)
    grupo['TELAS_SET']  = grupo['ESTILO_C'].apply(parse_telas)

    lotes = []
    lote_id_offset = 1
    usados = set()
    idxs = list(grupo.index)

    while True:
        disponibles = [i for i in idxs if i not in usados]
        if len(disponibles) < 2:
            break

        model  = cp_model.CpModel()
        x      = {i: model.NewBoolVar(f"x_{i}") for i in disponibles}

        total_lbs_expr = sum(int(grupo.loc[i, 'LBS_C']) * x[i] for i in disponibles)
        model.Add(total_lbs_expr >= int(min_lbs))
        model.Add(total_lbs_expr <= int(max_lbs))
        model.Add(sum(x[i] for i in disponibles) <= max_items)

        # Telas incompatibility
        for i in disponibles:
            for j in disponibles:
                if i < j:
                    inter = grupo.loc[i, 'TELAS_SET'] & grupo.loc[j, 'TELAS_SET']
                    if not inter:
                        model.Add(x[i] + x[j] <= 1)

        # Ancho control
        anchos_unicos = list(set().union(*grupo.loc[disponibles, 'ANCHOS_SET']))
        y = {a: model.NewBoolVar(f"ancho_{a}") for a in anchos_unicos}
        for i in disponibles:
            for a in grupo.loc[i, 'ANCHOS_SET']:
                model.Add(x[i] <= y[a])
        model.Add(sum(y[a] for a in anchos_unicos) <= max_anchos)

        model.Maximize(total_lbs_expr)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = solver_timeout
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break

        seleccion = [i for i in disponibles if solver.Value(x[i]) == 1]
        if len(seleccion) < 2:
            break

        suma = sum(grupo.loc[i, 'LBS_C'] for i in seleccion)
        for i in seleccion:
            usados.add(i)

        lotes.append((lote_id_offset, list(seleccion), suma))
        lote_id_offset += 1

    return lotes, grupo

def run_all(df, capacidades, config, rest_ancho_df, rest_color_df, rest_familia_df):
    max_items      = config.get('MAX_ITEMS', 8)
    solver_timeout = config.get('SOLVER_TIMEOUT', 5)

    all_results = []
    progress     = st.progress(0)
    status_txt   = st.empty()

    active_caps = [c for c in capacidades if c.get('ACTIVO', True)]

    for idx, cap in enumerate(active_caps):
        cat = cap['CATEGORIA']
        status_txt.markdown(f"<small>Procesando categoría **{cat}**...</small>", unsafe_allow_html=True)

        lotes, grupo = run_loteador(df, cap, max_items, solver_timeout,
                                     rest_ancho_df, rest_color_df, rest_familia_df)

        lote_global = 1
        for lid, indices, suma in lotes:
            for i in indices:
                row = grupo.loc[i].copy()
                row['CATEGORIA']    = cat
                row['LOTE_ID']      = f"{cat}-L{lid:03d}"
                row['TOTAL_LOTE']   = suma
                row['PCT_CARGA_REAL'] = round(suma / cap['MAXIMO'] * 100, 1)

                # Anchos del lote
                anchos_lote = set()
                for ii in indices:
                    anchos_lote |= grupo.loc[ii, 'ANCHOS_SET']
                ordenados = sorted(anchos_lote, key=lambda x: float(x), reverse=True)
                row['SET_ANCHOS_LOTE'] = "-".join(ordenados)
                row['CANT_ANCHOS']     = len(anchos_lote)

                # Tipo de lote
                c = len(anchos_lote)
                if c == 1:
                    row['TIPO_LOTE_ANCHO'] = 'PURO'
                elif c <= 3:
                    row['TIPO_LOTE_ANCHO'] = 'MIX_CONTROLADO'
                else:
                    row['TIPO_LOTE_ANCHO'] = 'MIX_ALTO'

                all_results.append(row)

        progress.progress((idx + 1) / len(active_caps))

    progress.empty()
    status_txt.empty()

    if not all_results:
        return pd.DataFrame()

    result_df = pd.DataFrame(all_results)
    cols_show = ['CATEGORIA','LOTE_ID','COLOR_A','ESTILO_C','ANCHO','LBS_C',
                 'TOTAL_LOTE','PCT_CARGA_REAL','SET_ANCHOS_LOTE','CANT_ANCHOS',
                 'TIPO_LOTE_ANCHO','MIX','TIPO_TEJIDO','PRIORIDAD','COLOR_R','FAMILIA']
    cols_show = [c for c in cols_show if c in result_df.columns]
    return result_df[cols_show].sort_values(['CATEGORIA','LOTE_ID'])

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding: 10px 0 16px 0;">
          <div style="font-size:22px; font-weight:800; color:white; letter-spacing:1px;">⚙ ELCATEX</div>
          <div style="font-size:9px; color:#cce4ff; letter-spacing:2px; text-transform:uppercase;">Loteador Óptimo v2.0</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**📁 Perfiles Guardados**")

        profiles = load_profiles()
        profile_names = list(profiles.keys())

        col1, col2 = st.columns([2,1])
        with col1:
            selected_profile = st.selectbox("Cargar perfil", ["(ninguno)"] + profile_names, label_visibility="collapsed")
        with col2:
            load_btn = st.button("Cargar", use_container_width=True)

        new_profile_name = st.text_input("Nombre para guardar", placeholder="Mi configuración...")
        save_btn = st.button("💾 Guardar Perfil", use_container_width=True)

        if load_btn and selected_profile != "(ninguno)":
            p = load_profile(selected_profile)
            if p:
                st.session_state['capacidades']          = p['capacidades']
                st.session_state['config']               = p['config']
                st.session_state['rest_ancho']           = p.get('rest_ancho', DEFAULT_RESTRICCIONES_ANCHO)
                st.session_state['rest_color']           = p.get('rest_color', DEFAULT_RESTRICCIONES_COLOR)
                st.session_state['rest_familia']         = p.get('rest_familia', DEFAULT_RESTRICCIONES_FAMILIA)
                st.session_state['anchos_combinados']    = p.get('anchos_combinados', [])
                st.success(f"✓ Perfil '{selected_profile}' cargado")

        if save_btn:
            if not new_profile_name.strip():
                st.warning("Escribe un nombre para el perfil")
            else:
                save_current_profile(
                    new_profile_name.strip(),
                    st.session_state.get('capacidades', DEFAULT_CAPACIDADES),
                    st.session_state.get('config', DEFAULT_CONFIG),
                    st.session_state.get('rest_ancho', DEFAULT_RESTRICCIONES_ANCHO),
                    st.session_state.get('rest_color', DEFAULT_RESTRICCIONES_COLOR),
                    st.session_state.get('rest_familia', DEFAULT_RESTRICCIONES_FAMILIA),
                    st.session_state.get('anchos_combinados', []),
                )
                st.success(f"✓ Guardado: '{new_profile_name.strip()}'")

        if profile_names:
            del_profile = st.selectbox("Eliminar perfil", [""] + profile_names, label_visibility="collapsed")
            if st.button("🗑 Eliminar", use_container_width=True) and del_profile:
                profiles = load_profiles()
                profiles.pop(del_profile, None)
                save_profiles(profiles)
                st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style="text-align:center; font-size:9px; color:#7fb3d8; margin-top:8px;">
          Grupo Elcatex · Lideramos. Cuidamos.<br>Hacemos la Diferencia.
        </div>
        """, unsafe_allow_html=True)

# ─── TAB: CAPACIDADES TINTO ──────────────────────────────────────────────────────
def tab_capacidades():
    st.markdown("### Capacidades de Tinto por Categoría")
    st.markdown("<small style='color:#7f8c8d'>Define mínimo, máximo, lotes y semanas. La capacidad LBS se calcula automáticamente: <b>Lotes × 7 días × Semanas × Máximo</b></small>", unsafe_allow_html=True)

    caps = st.session_state.get('capacidades', DEFAULT_CAPACIDADES)

    tipo_options = ["TODOS", "FLEECE", "JERSEY"]
    mix_options  = ["DYE", "BLEACH"]

    updated = []
    for i, cap in enumerate(caps):
        with st.container():
            cap_lbs = cap['LOTES'] * DIAS_SEMANA * cap['SEMANAS'] * cap['MAXIMO']
            activo  = cap.get('ACTIVO', True)
            card_class = "elc-card" if activo else "elc-card elc-card-gray"

            st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
            cols = st.columns([0.4, 1, 0.8, 0.8, 0.8, 0.8, 1, 0.8, 0.8, 0.8, 1.2, 0.5])

            with cols[0]:
                activo_new = st.checkbox("", value=activo, key=f"cap_activo_{i}", help="Activo/Inactivo")
            with cols[1]:
                cat = st.text_input("Categoría", cap['CATEGORIA'], key=f"cap_cat_{i}", label_visibility="collapsed")
                st.caption("Categoría")
            with cols[2]:
                minv = st.number_input("Mín", cap['MINIMO'], key=f"cap_min_{i}", step=100, label_visibility="collapsed")
                st.caption("Mínimo lbs")
            with cols[3]:
                maxv = st.number_input("Máx", cap['MAXIMO'], key=f"cap_max_{i}", step=100, label_visibility="collapsed")
                st.caption("Máximo lbs")
            with cols[4]:
                lotes = st.number_input("Lotes", cap['LOTES'], key=f"cap_lotes_{i}", step=1, min_value=1, label_visibility="collapsed")
                st.caption("Lotes")
            with cols[5]:
                semanas = st.number_input("Sem", cap['SEMANAS'], key=f"cap_sem_{i}", step=1, min_value=1, label_visibility="collapsed")
                st.caption("Semanas")
            with cols[6]:
                cap_calc = lotes * DIAS_SEMANA * semanas * maxv
                st.markdown(f"<div style='padding-top:6px'><span class='badge badge-blue'>{cap_calc:,} lbs</span></div>", unsafe_allow_html=True)
                st.caption("Cap. calculada")
            with cols[7]:
                min_ancho = st.number_input("MinA", cap.get('MIN_ANCHO',1), key=f"cap_mina_{i}", step=1, min_value=1, label_visibility="collapsed")
                st.caption("Min Ancho")
            with cols[8]:
                max_ancho = st.number_input("MaxA", cap.get('MAX_ANCHO',4), key=f"cap_maxa_{i}", step=1, min_value=1, label_visibility="collapsed")
                st.caption("Max Ancho")
            with cols[9]:
                ctd_anchos = st.number_input("CtdA", cap.get('CTDMAXANCHOS',3), key=f"cap_ctda_{i}", step=1, min_value=1, max_value=10, label_visibility="collapsed")
                st.caption("Ctd Max Anchos")
            with cols[10]:
                mix_sel = st.selectbox("MIX", mix_options, index=mix_options.index(cap.get('MIX','DYE')), key=f"cap_mix_{i}", label_visibility="collapsed")
                st.caption("MIX")
            with cols[11]:
                tipo_sel = st.selectbox("Tejido", tipo_options, index=tipo_options.index(cap.get('TIPO_TEJIDO','TODOS')), key=f"cap_tipo_{i}", label_visibility="collapsed")
                st.caption("Tipo Tejido")

            st.markdown("</div>", unsafe_allow_html=True)

            updated.append({
                "CATEGORIA": cat, "MINIMO": minv, "MAXIMO": maxv,
                "LOTES": lotes, "SEMANAS": semanas,
                "MIN_ANCHO": min_ancho, "MAX_ANCHO": max_ancho,
                "CTDMAXANCHOS": ctd_anchos, "MIX": mix_sel,
                "TIPO_TEJIDO": tipo_sel, "ACTIVO": activo_new,
                "CAPACIDAD_LBS": cap_calc,
            })

    # Add new row
    if st.button("➕ Agregar Categoría"):
        updated.append({"CATEGORIA":"NUEVA","MINIMO":1000,"MAXIMO":1100,"LOTES":5,"SEMANAS":4,
                        "MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"DYE","TIPO_TEJIDO":"TODOS","ACTIVO":True,"CAPACIDAD_LBS":0})

    st.session_state['capacidades'] = updated


# ─── TAB: RESTRICCIONES ──────────────────────────────────────────────────────────
def editable_rest_table(data, cols_def, key_prefix, title, help_text=""):
    st.markdown(f"**{title}**")
    if help_text:
        st.caption(help_text)

    updated = []
    for i, row in enumerate(data):
        c_list = st.columns([0.4] + [1]*len(cols_def) + [0.3])
        activo = c_list[0].checkbox("", value=row.get('ACTIVO', True), key=f"{key_prefix}_act_{i}")
        vals = {}
        for j, (col, col_type, default) in enumerate(cols_def):
            widget_col = c_list[j+1]
            if col_type == 'text':
                vals[col] = widget_col.text_input(col, value=str(row.get(col,'')), key=f"{key_prefix}_{col}_{i}", label_visibility="collapsed")
            elif col_type == 'number_opt':
                raw = row.get(col, None)
                txt = widget_col.text_input(col, value=str(int(raw)) if raw else '', key=f"{key_prefix}_{col}_{i}", label_visibility="collapsed", placeholder="—")
                vals[col] = int(txt) if txt.strip().isdigit() else None
            elif col_type == 'number':
                vals[col] = widget_col.number_input(col, value=float(row.get(col, default) or default), key=f"{key_prefix}_{col}_{i}", step=1.0, label_visibility="collapsed")
        vals['ACTIVO'] = activo
        updated.append(vals)

        # delete button
        if c_list[-1].button("✕", key=f"{key_prefix}_del_{i}"):
            updated.pop()

    if st.button(f"➕ Agregar fila", key=f"{key_prefix}_add"):
        new_row = {col: default for col, _, default in cols_def}
        new_row['ACTIVO'] = True
        updated.append(new_row)

    return updated


def tab_restricciones():
    st.markdown("### Restricciones de Asignación")

    t1, t2, t3, t4 = st.tabs(["🔩 Restricciones Ancho", "🎨 Restricciones Color", "👕 Restricciones Familia", "📐 Anchos Combinados"])

    with t1:
        rest_ancho = st.session_state.get('rest_ancho', DEFAULT_RESTRICCIONES_ANCHO)
        cols_def = [
            ('STYLE',       'text',       ''),
            ('LIMITE_ANCHO','number',     18),
            ('PRIORIDAD_1', 'number_opt', None),
            ('PRIORIDAD_2', 'number_opt', None),
            ('PRIORIDAD_3', 'number_opt', None),
        ]
        st.markdown("<div style='display:flex; gap:8px; margin-bottom:4px; font-size:10px; color:#7f8c8d; font-weight:600;'>"
                    "<span style='width:30px'>&nbsp;</span>"
                    "<span style='flex:1'>STYLE</span><span style='flex:1'>LIMITE_ANCHO</span>"
                    "<span style='flex:1'>PRIORIDAD_1</span><span style='flex:1'>PRIORIDAD_2</span>"
                    "<span style='flex:1'>PRIORIDAD_3</span><span style='width:30px'></span></div>", unsafe_allow_html=True)
        updated = editable_rest_table(rest_ancho, cols_def, "ra", "", "STYLEs con restricción de ancho máximo y categoría destino")
        st.session_state['rest_ancho'] = updated

    with t2:
        rest_color = st.session_state.get('rest_color', DEFAULT_RESTRICCIONES_COLOR)
        cols_def = [
            ('COLOR_R',    'text',       ''),
            ('PRIORIDAD_1','number_opt', None),
            ('PRIORIDAD_2','number_opt', None),
            ('PRIORIDAD_3','number_opt', None),
        ]
        st.markdown("<div style='display:flex; gap:8px; margin-bottom:4px; font-size:10px; color:#7f8c8d; font-weight:600;'>"
                    "<span style='width:30px'>&nbsp;</span>"
                    "<span style='flex:1'>COLOR_R</span>"
                    "<span style='flex:1'>PRIORIDAD_1</span><span style='flex:1'>PRIORIDAD_2</span>"
                    "<span style='flex:1'>PRIORIDAD_3</span><span style='width:30px'></span></div>", unsafe_allow_html=True)
        updated = editable_rest_table(rest_color, cols_def, "rc", "", "Colores con restricción de categoría")
        st.session_state['rest_color'] = updated

    with t3:
        rest_familia = st.session_state.get('rest_familia', DEFAULT_RESTRICCIONES_FAMILIA)
        cols_def = [
            ('FAMILIA',    'text',       ''),
            ('PRIORIDAD_1','number_opt', None),
            ('PRIORIDAD_2','number_opt', None),
            ('PRIORIDAD_3','number_opt', None),
            ('PRIORIDAD_4','number_opt', None),
        ]
        st.markdown("<div style='display:flex; gap:8px; margin-bottom:4px; font-size:10px; color:#7f8c8d; font-weight:600;'>"
                    "<span style='width:30px'>&nbsp;</span>"
                    "<span style='flex:1'>FAMILIA</span>"
                    "<span style='flex:1'>PRIORIDAD_1</span><span style='flex:1'>PRIORIDAD_2</span>"
                    "<span style='flex:1'>PRIORIDAD_3</span><span style='flex:1'>PRIORIDAD_4</span>"
                    "<span style='width:30px'></span></div>", unsafe_allow_html=True)
        updated = editable_rest_table(rest_familia, cols_def, "rf", "", "Familias de producto con restricción de categoría destino")
        st.session_state['rest_familia'] = updated

    with t4:
        st.markdown("**Reglas de Anchos Combinados**")
        st.caption("Define a qué capacidad dirigir un lote cuando combina ciertos anchos específicos")
        anchos_comb = st.session_state.get('anchos_combinados', [])
        cols_def = [
            ('ANCHO_1',               'number', 18),
            ('ANCHO_2',               'number', 20),
            ('CAPACIDAD_PRIORIDAD_1', 'number_opt', None),
            ('CAPACIDAD_PRIORIDAD_2', 'number_opt', None),
            ('CAPACIDAD_PRIORIDAD_3', 'number_opt', None),
        ]
        st.markdown("<div style='display:flex; gap:8px; margin-bottom:4px; font-size:10px; color:#7f8c8d; font-weight:600;'>"
                    "<span style='width:30px'>&nbsp;</span>"
                    "<span style='flex:1'>ANCHO_1</span><span style='flex:1'>ANCHO_2</span>"
                    "<span style='flex:1'>CAP_PRIO_1</span><span style='flex:1'>CAP_PRIO_2</span>"
                    "<span style='flex:1'>CAP_PRIO_3</span><span style='width:30px'></span></div>", unsafe_allow_html=True)
        updated = editable_rest_table(anchos_comb, cols_def, "ac", "", "")
        st.session_state['anchos_combinados'] = updated


# ─── TAB: CONFIG AVANZADA ────────────────────────────────────────────────────────
def tab_config():
    st.markdown("### Configuración Avanzada del Solver")
    config = st.session_state.get('config', DEFAULT_CONFIG)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='elc-card'>", unsafe_allow_html=True)
        st.markdown("**🔧 Parámetros del Solver**")
        max_items = st.number_input("MAX_ITEMS (máx. SKUs por lote)", value=config.get('MAX_ITEMS',8), min_value=2, max_value=20, step=1,
                                     help="Máximo de ítems que puede tener un lote")
        solver_timeout = st.number_input("Tiempo máximo solver (seg)", value=config.get('SOLVER_TIMEOUT',5), min_value=1, max_value=60, step=1,
                                          help="Tiempo límite del optimizador por lote")
        apply_bleach = st.checkbox("Aplicar reglas especiales BLEACH", value=config.get('APPLY_RULES_BLEACH', False))
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='elc-card'>", unsafe_allow_html=True)
        st.markdown("**🔀 Combinación de Prioridades**")
        st.caption("Define qué valores de PRIORIDAD pueden combinarse en un mismo lote")
        combo = config.get('COMBINACION_PRIORIDAD', [["VENCIDOS","AHEAD"],["AHEAD","AHEAD2"],["AHEAD2","OTROS"]])
        combo_txt = st.text_area("Pares permitidos (uno por línea: P1,P2)", value="\n".join([",".join(p) for p in combo]), height=100)
        try:
            combo_parsed = [line.strip().split(",") for line in combo_txt.strip().split("\n") if "," in line]
        except:
            combo_parsed = combo
        st.markdown("</div>", unsafe_allow_html=True)

    st.session_state['config'] = {
        "MAX_ITEMS": max_items,
        "SOLVER_TIMEOUT": solver_timeout,
        "APPLY_RULES_BLEACH": apply_bleach,
        "COMBINACION_PRIORIDAD": combo_parsed,
    }


# ─── TAB: EJECUTAR ───────────────────────────────────────────────────────────────
def tab_ejecutar():
    st.markdown("### Cargar Datos y Ejecutar Loteador")

    uploaded = st.file_uploader("📂 Sube el archivo Excel (hoja DATA)", type=["xlsx"], help="El archivo debe contener la hoja DATA con header en fila 3 (fila 1 y 2 vacías)")

    if uploaded:
        file_bytes = uploaded.read()
        df_raw, err = read_excel_data(file_bytes)
        if err:
            st.error(err)
            return

        df = build_join_from_data(df_raw)
        if df is None:
            return

        st.session_state['df_cargado'] = df

        # Preview
        st.markdown("<div class='elc-card'>", unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        c1.markdown(f"<div class='metric-box'><div class='metric-val'>{len(df):,}</div><div class='metric-lbl'>Registros</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'><div class='metric-val'>{df['COLOR_A'].nunique():,}</div><div class='metric-lbl'>Colores</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'><div class='metric-val'>{df['MIX'].nunique()}</div><div class='metric-lbl'>Tipos MIX</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-box'><div class='metric-val'>{df['LBS_C'].sum():,.0f}</div><div class='metric-lbl'>Total LBS</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("👁 Vista previa de datos"):
            st.dataframe(df[['COLOR_A','ESTILO_C','ANCHO','LBS_C','MIX','TIPO_TEJIDO','PCT_CARGA','COLOR_R','FAMILIA','PRIORIDAD']].head(30), use_container_width=True, height=250)

    # Run button
    st.markdown("---")
    col_run, col_info = st.columns([1,3])
    with col_run:
        run_btn = st.button("▶  EJECUTAR LOTEADOR", use_container_width=True)

    with col_info:
        caps_activas = [c for c in st.session_state.get('capacidades', DEFAULT_CAPACIDADES) if c.get('ACTIVO', True)]
        st.markdown(f"<small style='color:#7f8c8d'>Se procesarán <b>{len(caps_activas)}</b> categorías activas con los parámetros configurados.</small>", unsafe_allow_html=True)

    if run_btn:
        df = st.session_state.get('df_cargado', None)
        if df is None:
            st.warning("⚠ Primero sube un archivo Excel con la hoja DATA.")
            return

        caps     = st.session_state.get('capacidades', DEFAULT_CAPACIDADES)
        config   = st.session_state.get('config', DEFAULT_CONFIG)

        rest_ancho_df   = pd.DataFrame(st.session_state.get('rest_ancho', DEFAULT_RESTRICCIONES_ANCHO))
        rest_color_df   = pd.DataFrame(st.session_state.get('rest_color', DEFAULT_RESTRICCIONES_COLOR))
        rest_familia_df = pd.DataFrame(st.session_state.get('rest_familia', DEFAULT_RESTRICCIONES_FAMILIA))

        with st.spinner("Ejecutando optimización..."):
            result = run_all(df, caps, config, rest_ancho_df, rest_color_df, rest_familia_df)

        if result.empty:
            st.warning("No se generaron lotes. Revisa los parámetros y los datos.")
        else:
            st.session_state['resultado'] = result
            st.success(f"✅ Loteador completado: **{result['LOTE_ID'].nunique()} lotes** generados con **{len(result)} registros**")

# ─── TAB: RESULTADOS ─────────────────────────────────────────────────────────────
def tab_resultados():
    st.markdown("### Resultados del Loteador")

    result = st.session_state.get('resultado', None)
    if result is None:
        st.info("Aún no hay resultados. Ve a la pestaña **Ejecutar** para correr el loteador.")
        return

    # Summary metrics
    n_lotes    = result['LOTE_ID'].nunique()
    total_lbs  = result.groupby('LOTE_ID')['TOTAL_LOTE'].first().sum()
    cats_usadas = result['CATEGORIA'].nunique()
    puro_pct   = round((result[result['TIPO_LOTE_ANCHO']=='PURO']['LOTE_ID'].nunique() / n_lotes * 100), 1) if n_lotes else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='metric-box'><div class='metric-val'>{n_lotes}</div><div class='metric-lbl'>Lotes Generados</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-box'><div class='metric-val'>{total_lbs:,.0f}</div><div class='metric-lbl'>Total LBS Loteadas</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-box'><div class='metric-val'>{cats_usadas}</div><div class='metric-lbl'>Categorías Usadas</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-box'><div class='metric-val'>{puro_pct}%</div><div class='metric-lbl'>Lotes Puros</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        cats = ["Todas"] + sorted(result['CATEGORIA'].unique().tolist())
        cat_sel = st.selectbox("Filtrar Categoría", cats)
    with col_f2:
        tipos = ["Todos"] + sorted(result['TIPO_LOTE_ANCHO'].dropna().unique().tolist())
        tipo_sel = st.selectbox("Filtrar Tipo Lote", tipos)
    with col_f3:
        mix_opts = ["Todos"] + sorted(result['MIX'].dropna().unique().tolist())
        mix_sel = st.selectbox("Filtrar MIX", mix_opts)

    df_show = result.copy()
    if cat_sel  != "Todas": df_show = df_show[df_show['CATEGORIA']  == cat_sel]
    if tipo_sel != "Todos": df_show = df_show[df_show['TIPO_LOTE_ANCHO'] == tipo_sel]
    if mix_sel  != "Todos": df_show = df_show[df_show['MIX']        == mix_sel]

    st.dataframe(df_show, use_container_width=True, height=400)

    # Resumen por categoría
    with st.expander("📊 Resumen por Categoría"):
        resumen = result.groupby('CATEGORIA').agg(
            Lotes=('LOTE_ID','nunique'),
            Registros=('LOTE_ID','count'),
            LBS_Total=('TOTAL_LOTE', lambda x: result.loc[x.index].groupby('LOTE_ID')['TOTAL_LOTE'].first().sum()),
            Lotes_Puros=('TIPO_LOTE_ANCHO', lambda x: (x=='PURO').sum()),
            Lotes_MixControlado=('TIPO_LOTE_ANCHO', lambda x: (x=='MIX_CONTROLADO').sum()),
        ).reset_index()
        st.dataframe(resumen, use_container_width=True)

    # Download
    st.markdown("---")
    st.markdown("**📥 Exportar Resultados**")

    tz = pytz.timezone("America/Tegucigalpa")
    ts = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    fname = f"loteo_OPTIMO_{ts}.xlsx"

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        result.to_excel(writer, sheet_name='LOTES', index=False)
        if 'resultado' in st.session_state:
            resumen_dl = result.groupby('CATEGORIA').agg(
                Lotes=('LOTE_ID','nunique'),
                LBS_Total=('LBS_C','sum'),
            ).reset_index()
            resumen_dl.to_excel(writer, sheet_name='RESUMEN', index=False)
    buf.seek(0)

    st.download_button("⬇ Descargar Excel", data=buf, file_name=fname,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ─── MAIN ────────────────────────────────────────────────────────────────────────
def main():
    sidebar()

    # Header
    st.markdown("""
    <div class="logo-header">
      <div>
        <div class="logo-title">🏭 Loteador Óptimo de Tintorería</div>
        <div class="logo-sub">Grupo Elcatex · Optimización con OR-Tools · Honduras</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Capacidades Tinto",
        "🔒 Restricciones",
        "⚙ Configuración",
        "▶ Ejecutar",
        "📋 Resultados",
    ])

    with tab1: tab_capacidades()
    with tab2: tab_restricciones()
    with tab3: tab_config()
    with tab4: tab_ejecutar()
    with tab5: tab_resultados()

if __name__ == "__main__":
    main()
