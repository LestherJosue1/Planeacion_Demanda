import streamlit as st
import pandas as pd
import json
import os
import time
import threading
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

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 12px; }
  .stApp { background-color: #f4f6f9; }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #003876 0%, #0057a8 60%, #0080c9 100%);
  }
  [data-testid="stSidebar"] * { color: #ffffff !important; font-size: 11.5px !important; }
  [data-testid="stSidebar"] input { color: #1a1a2e !important; background: #ffffff !important; border-radius: 4px !important; }
  [data-testid="stSidebar"] input::placeholder { color: #999 !important; }
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stNumberInput label,
  [data-testid="stSidebar"] .stTextInput label { color: #cce4ff !important; font-weight: 500 !important; }
  h1 { color: #003876 !important; font-size: 20px !important; font-weight: 700 !important; }
  h2 { color: #0057a8 !important; font-size: 15px !important; font-weight: 600 !important; }
  h3 { color: #003876 !important; font-size: 13px !important; font-weight: 600 !important; }
  .elc-card {
    background: white; border-radius: 8px; padding: 14px 18px;
    border-left: 4px solid #0057a8; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 10px;
  }
  .elc-card-gray { border-left-color: #bdc3c7 !important; opacity: 0.7; }
  .metric-box {
    background: white; border-radius: 8px; padding: 14px 16px;
    text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }
  .metric-val { font-size: 22px; font-weight: 700; color: #003876; }
  .metric-lbl { font-size: 10px; color: #7f8c8d; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
  .stButton > button {
    background: linear-gradient(135deg, #0057a8, #003876);
    color: white !important; border: none; border-radius: 6px;
    font-size: 12px; font-weight: 600; padding: 8px 20px; transition: all 0.2s;
  }
  .stButton > button:hover { background: linear-gradient(135deg, #0080c9, #0057a8); box-shadow: 0 3px 10px rgba(0,87,168,0.4); }
  .stDataFrame { border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .stTabs [data-baseweb="tab-list"] { background: white; border-radius: 8px 8px 0 0; gap: 2px; padding: 4px; }
  .stTabs [data-baseweb="tab"] { font-size: 11.5px; font-weight: 600; color: #7f8c8d; border-radius: 6px; }
  .stTabs [aria-selected="true"] { background: #0057a8 !important; color: white !important; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-green { background: #d1fae5; color: #065f46; }
  .badge-orange { background: #ffedd5; color: #9a3412; }
  .badge-gray { background: #f1f5f9; color: #475569; }
  .logo-header {
    background: linear-gradient(135deg, #003876, #0057a8);
    border-radius: 10px; padding: 14px 20px; margin-bottom: 16px;
  }
  .col-header { font-size: 9px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
  div[data-testid="stNumberInput"] input { font-size: 11px !important; padding: 4px 6px !important; }
  div[data-testid="stTextInput"] input { font-size: 11px !important; padding: 4px 6px !important; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ──────────────────────────────────────────────────────────────────
PROFILES_FILE = "elcatex_profiles.json"
DIAS_SEMANA   = 7

DEFAULT_CAPACIDADES = [
    {"CATEGORIA":"A-4000","MINIMO":3900,"MAXIMO":4000,"LOTES":5, "SEMANAS":4,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":4,"MIX":"DYE",   "TIPO_TEJIDO":"FLEECE","ACTIVO":True},
    {"CATEGORIA":"B-3300","MINIMO":3000,"MAXIMO":3300,"LOTES":6, "SEMANAS":4,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":4,"MIX":"DYE",   "TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"C-2600","MINIMO":2500,"MAXIMO":2600,"LOTES":29,"SEMANAS":4,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"DYE",   "TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"D-2200","MINIMO":2000,"MAXIMO":2200,"LOTES":17,"SEMANAS":4,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"DYE",   "TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"E-1100","MINIMO":1000,"MAXIMO":1100,"LOTES":25,"SEMANAS":4,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":2,"MIX":"DYE",   "TIPO_TEJIDO":"JERSEY","ACTIVO":True},
    {"CATEGORIA":"F-2200","MINIMO":2000,"MAXIMO":2200,"LOTES":21,"SEMANAS":4,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"BLEACH","TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"G-1100","MINIMO":1000,"MAXIMO":1100,"LOTES":4, "SEMANAS":4,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":2,"MIX":"BLEACH","TIPO_TEJIDO":"TODOS", "ACTIVO":True},
]

DEFAULT_CONFIG = {
    "MAX_ITEMS": 8,
    "SOLVER_TIMEOUT": 5,
    "COMBINACION_PRIORIDAD": [["VENCIDOS","AHEAD"],["AHEAD","AHEAD2"],["AHEAD2","OTROS"]],
    "APPLY_RULES_BLEACH": False,
}

DEFAULT_RESTRICCIONES_ANCHO = [
    {"STYLE":"PC54Y",  "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC55LS", "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC55Y",  "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC330Y", "LIMITE_ANCHO":18,"PRIORIDAD_1":2200,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC54-2", "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
]

DEFAULT_RESTRICCIONES_COLOR = [
    {"COLOR_R":"RESTRICCION","PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"COLOR_R":"NORMAL",     "PRIORIDAD_1":None,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
]

DEFAULT_RESTRICCIONES_FAMILIA = [
    {"FAMILIA":"PC68",   "PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"PRIORIDAD_4":None,"ACTIVO":True},
    {"FAMILIA":"PC850",  "PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"PRIORIDAD_4":None,"ACTIVO":True},
    {"FAMILIA":"PC78/90","PRIORIDAD_1":4000,"PRIORIDAD_2":2600,"PRIORIDAD_3":3300,"PRIORIDAD_4":None,"ACTIVO":True},
]

# ─── HELPERS ────────────────────────────────────────────────────────────────────
def to_int(v, default=0):
    """Safe int cast — handles float, str, None from JSON."""
    try:
        return int(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def to_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def safe_mix_index(val, options):
    v = str(val).upper().strip()
    for i, o in enumerate(options):
        if o.upper() == v:
            return i
    return 0

def safe_str_index(val, options, default=0):
    v = str(val).strip()
    for i, o in enumerate(options):
        if o == v:
            return i
    return default

# ─── PROFILES ───────────────────────────────────────────────────────────────────
def load_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            return json.load(f)
    return {}

def save_profiles(profiles):
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2, default=str)

def save_current_profile(name):
    profiles = load_profiles()
    profiles[name] = {
        "capacidades":       st.session_state.get("capacidades", DEFAULT_CAPACIDADES),
        "config":            st.session_state.get("config",      DEFAULT_CONFIG),
        "rest_ancho":        st.session_state.get("rest_ancho",  DEFAULT_RESTRICCIONES_ANCHO),
        "rest_color":        st.session_state.get("rest_color",  DEFAULT_RESTRICCIONES_COLOR),
        "rest_familia":      st.session_state.get("rest_familia",DEFAULT_RESTRICCIONES_FAMILIA),
        "anchos_combinados": st.session_state.get("anchos_combinados", []),
        "saved_at": datetime.now().isoformat(),
    }
    save_profiles(profiles)

# ─── DATA ───────────────────────────────────────────────────────────────────────
def build_join_from_data(df_raw):
    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.replace('\xa0','',regex=True)

    needed = ['STYLE','COLOR','TELA.CUERPO','ANCHO.F.C','TOTAL','MIX','COLOR_R','FAMILIA','PRIORIDAD']
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.error(f"Columnas faltantes en DATA: {missing}")
        return None

    if 'TIPO_TEJIDO' not in df.columns:
        df['TIPO_TEJIDO'] = 'TODOS'
    if 'PCT_CARGA' not in df.columns:
        df['PCT_CARGA'] = 1.0

    df = df.rename(columns={
        'COLOR':       'COLOR_A',
        'TELA.CUERPO': 'ESTILO_C',
        'ANCHO.F.C':   'ANCHO',
        'TOTAL':       'LBS_C',
    })

    df['LBS_C']     = pd.to_numeric(df['LBS_C'],   errors='coerce')
    df['ANCHO']     = pd.to_numeric(df['ANCHO'],   errors='coerce')
    df['PCT_CARGA'] = pd.to_numeric(df['PCT_CARGA'],errors='coerce').fillna(1.0)
    df['MIX']       = df['MIX'].str.upper().str.strip()
    df['MIX_ANCHOS']= df['ANCHO'].astype(str)

    df = df.dropna(subset=['LBS_C','ANCHO','COLOR_A','ESTILO_C']).reset_index(drop=True)
    return df

@st.cache_data(show_spinner=False)
def read_excel_data(file_bytes):
    xl = pd.ExcelFile(BytesIO(file_bytes))
    if 'DATA' not in xl.sheet_names:
        return None, "No se encontró la hoja DATA."
    df_raw = pd.read_excel(BytesIO(file_bytes), sheet_name='DATA', header=2)
    return df_raw, None

# ─── LOTEADOR ───────────────────────────────────────────────────────────────────
def _parse_set(x):
    return set(str(x).split("-"))

def _solver_params(timeout):
    """OR-Tools SAT parameters — compatibles con Streamlit Cloud (1 worker)."""
    p = cp_model.SatParameters()
    p.max_time_in_seconds = float(timeout)
    p.num_search_workers  = 1   # Streamlit Cloud: 1 CPU, mas de 1 causa OOM
    p.cp_model_presolve   = True
    p.log_search_progress = False
    return p

def _prefilter(grupo, min_lbs, max_lbs, max_items):
    """
    Elimina filas que NUNCA pueden integrarse a un lote válido:
      - Un ítem solo: si su LBS > max_lbs, no puede entrar en ningún lote.
      - Si hay menos de 2 ítems con LBS <= max_lbs, no hay lote posible.
    Retorna índices válidos.
    """
    mask  = grupo['LBS_C'] <= max_lbs
    valid = list(grupo[mask].index)
    return valid

def _solve_one_group(grupo, idxs_disp, usados, min_lbs, max_lbs, max_anchos, max_items, solver_params):
    """
    Resuelve un subproblema para los índices disponibles dentro de un grupo COLOR_A.
    Retorna (indices_seleccionados, suma_lbs) o ([], 0) si no hay solución.
    """
    disponibles = [i for i in idxs_disp if i not in usados]
    if len(disponibles) < 2:
        return [], 0

    # Pre-filtro rápido: descartar ítems que por sí solos exceden el máximo
    disponibles = [i for i in disponibles if grupo.loc[i,'LBS_C'] <= max_lbs]
    if len(disponibles) < 2:
        return [], 0

    model = cp_model.CpModel()
    x     = {i: model.NewBoolVar(f"x{i}") for i in disponibles}

    lbs_vals = [int(grupo.loc[i,'LBS_C']) for i in disponibles]
    lbs_expr = sum(v * x[i] for v, i in zip(lbs_vals, disponibles))

    model.Add(lbs_expr >= int(min_lbs))
    model.Add(lbs_expr <= int(max_lbs))
    model.Add(sum(x[i] for i in disponibles) <= int(max_items))

    # Incompatibilidad de telas (solo pares con CERO intersección)
    for ii, i in enumerate(disponibles):
        for j in disponibles[ii+1:]:
            if not (grupo.loc[i,'TELAS_SET'] & grupo.loc[j,'TELAS_SET']):
                model.Add(x[i] + x[j] <= 1)

    # Control de anchos
    anchos_unicos = list(set().union(*grupo.loc[disponibles,'ANCHOS_SET']))
    y = {a: model.NewBoolVar(f"y{a}") for a in anchos_unicos}
    for i in disponibles:
        for a in grupo.loc[i,'ANCHOS_SET']:
            model.Add(x[i] <= y[a])
    model.Add(sum(y[a] for a in anchos_unicos) <= int(max_anchos))

    model.Maximize(lbs_expr)

    solver = cp_model.CpSolver()
    solver.parameters.CopyFrom(solver_params)
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return [], 0

    sel  = [i for i in disponibles if solver.Value(x[i]) == 1]
    suma = sum(grupo.loc[i,'LBS_C'] for i in sel)

    if len(sel) < 2 or suma < min_lbs:
        return [], 0

    return sel, suma


def run_loteador(df_cat, cap, max_items, solver_timeout):
    """
    Loteador principal.
    Agrupa por COLOR_A (igual que el código Colab original) y resuelve
    cada color independientemente — esto es lo que mantiene el tiempo corto.
    """
    min_lbs    = to_int(cap['MINIMO'])
    max_lbs    = to_int(cap['MAXIMO'])
    mix_tipo   = str(cap['MIX']).upper()
    tipo_tej   = str(cap['TIPO_TEJIDO']).upper()
    max_anchos = to_int(cap['CTDMAXANCHOS'], 3)

    # Filtros de categoría
    grupo_cat = df_cat[df_cat['MIX'].str.upper() == mix_tipo].copy()
    if tipo_tej != 'TODOS':
        grupo_cat = grupo_cat[grupo_cat['TIPO_TEJIDO'].str.upper().isin([tipo_tej, 'TODOS'])]

    if grupo_cat.empty:
        return [], grupo_cat

    grupo_cat['ANCHOS_SET'] = grupo_cat['MIX_ANCHOS'].apply(_parse_set)
    grupo_cat['TELAS_SET']  = grupo_cat['ESTILO_C'].apply(_parse_set)

    sparams = _solver_params(solver_timeout)
    lotes   = []
    lid     = 1

    # ── AGRUPACIÓN POR COLOR_A (clave de velocidad) ──────────────────────────
    for color, grupo in grupo_cat.groupby('COLOR_A'):
        idxs   = _prefilter(grupo, min_lbs, max_lbs, max_items)
        usados = set()

        while True:
            sel, suma = _solve_one_group(
                grupo, idxs, usados,
                min_lbs, max_lbs, max_anchos, max_items, sparams
            )
            if not sel:
                break
            for i in sel:
                usados.add(i)
            lotes.append((lid, sel, suma))
            lid += 1

    return lotes, grupo_cat


def run_all(df, capacidades, config):
    max_items      = to_int(config.get('MAX_ITEMS', 8))
    solver_timeout = to_float(config.get('SOLVER_TIMEOUT', 5))
    active_caps    = [c for c in capacidades if c.get('ACTIVO', True)]

    all_rows  = []
    log_lines = []

    for idx, cap in enumerate(active_caps):
        cat = cap['CATEGORIA']

        lotes, grupo = run_loteador(df, cap, max_items, solver_timeout)

        for lid, indices, suma in lotes:
            anchos_lote = set()
            for i in indices:
                anchos_lote |= grupo.loc[i,'ANCHOS_SET']
            ordenados  = sorted(anchos_lote, key=lambda a: float(a), reverse=True)
            set_anchos = "-".join(ordenados)
            cant       = len(anchos_lote)
            tipo_lote  = 'PURO' if cant == 1 else ('MIX_CONTROLADO' if cant <= 3 else 'MIX_ALTO')

            for i in indices:
                row = grupo.loc[i].copy()
                row['CATEGORIA']       = cat
                row['LOTE_ID']         = f"{cat}-L{lid:03d}"
                row['TOTAL_LOTE']      = round(suma, 1)
                row['PCT_CARGA_REAL']  = round(suma / max(to_int(cap['MAXIMO'], 1), 1) * 100, 1)
                row['SET_ANCHOS_LOTE'] = set_anchos
                row['CANT_ANCHOS']     = cant
                row['TIPO_LOTE_ANCHO'] = tipo_lote
                all_rows.append(row)

    if not all_rows:
        return pd.DataFrame()

    result = pd.DataFrame(all_rows)
    show   = ['CATEGORIA','LOTE_ID','COLOR_A','ESTILO_C','ANCHO','LBS_C',
              'TOTAL_LOTE','PCT_CARGA_REAL','SET_ANCHOS_LOTE','CANT_ANCHOS',
              'TIPO_LOTE_ANCHO','MIX','TIPO_TEJIDO','PCT_CARGA','PRIORIDAD','COLOR_R','FAMILIA']
    show   = [c for c in show if c in result.columns]
    return result[show].sort_values(['CATEGORIA','LOTE_ID']).reset_index(drop=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:10px 0 16px 0;">
          <div style="font-size:20px;font-weight:800;color:white;letter-spacing:1px;">⚙ ELCATEX</div>
          <div style="font-size:9px;color:#cce4ff;letter-spacing:2px;text-transform:uppercase;">Loteador Óptimo v2.0</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**📁 Perfiles**")

        profiles = load_profiles()
        names    = list(profiles.keys())

        col1, col2 = st.columns([2,1])
        with col1:
            sel = st.selectbox("Perfil", ["(ninguno)"] + names, label_visibility="collapsed")
        with col2:
            if st.button("Cargar", use_container_width=True) and sel != "(ninguno)":
                p = profiles[sel]
                for k in ("capacidades","config","rest_ancho","rest_color","rest_familia","anchos_combinados"):
                    if k in p:
                        st.session_state[k] = p[k]
                st.success(f"✓ '{sel}' cargado")
                st.rerun()

        new_name = st.text_input("Nombre del perfil", placeholder="Mi configuracion...",
                                  label_visibility="visible")
        col_s, col_d = st.columns(2)
        with col_s:
            if st.button("💾 Guardar", use_container_width=True):
                if new_name.strip():
                    save_current_profile(new_name.strip())
                    st.success(f"Guardado: {new_name.strip()}")
                else:
                    st.warning("Escribe un nombre")

        # Descarga del perfil seleccionado como JSON
        if sel != "(ninguno)" and sel in profiles:
            profile_json = json.dumps(profiles[sel], indent=2, default=str).encode()
            with col_d:
                st.download_button(
                    "⬇ JSON",
                    data=profile_json,
                    file_name=f"perfil_{sel}.json",
                    mime="application/json",
                    use_container_width=True,
                )

        if names:
            st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
            del_sel = st.selectbox("Eliminar perfil", [""] + names, label_visibility="collapsed")
            if st.button("🗑 Eliminar seleccionado", use_container_width=True) and del_sel:
                profiles.pop(del_sel, None)
                save_profiles(profiles)
                st.rerun()

        st.markdown("---")
        st.markdown("""<div style="text-align:center;font-size:9px;color:#7fb3d8;margin-top:8px;">
          Grupo Elcatex · Lideramos. Cuidamos.<br>Hacemos la Diferencia.</div>""", unsafe_allow_html=True)

# ─── TAB 1: CAPACIDADES ─────────────────────────────────────────────────────────
def tab_capacidades():
    st.markdown("### Capacidades de Tinto por Categoría")
    st.caption("Capacidad LBS = Lotes × 7 días × Semanas × Máximo lbs")

    caps         = st.session_state.get('capacidades', DEFAULT_CAPACIDADES)
    tipo_options = ["TODOS","FLEECE","JERSEY"]
    mix_options  = ["DYE","BLEACH"]

    # Column headers
    hcols = st.columns([0.35, 1.1, 0.75, 0.75, 0.65, 0.65, 0.95, 0.65, 0.65, 0.75, 0.85, 0.85])
    for col, lbl in zip(hcols, ["","Categoría","Mín lbs","Máx lbs","Lotes","Semanas","Cap LBS calc","Min Ancho","Max Ancho","Ctd Anchos","MIX","Tipo Tejido"]):
        col.markdown(f"<div class='col-header'>{lbl}</div>", unsafe_allow_html=True)

    updated = []
    for i, cap in enumerate(caps):
        activo = bool(cap.get('ACTIVO', True))
        c = st.columns([0.35, 1.1, 0.75, 0.75, 0.65, 0.65, 0.95, 0.65, 0.65, 0.75, 0.85, 0.85])

        activo_new  = c[0].checkbox("", value=activo, key=f"ca_{i}")
        cat         = c[1].text_input("", value=str(cap.get('CATEGORIA','')),  key=f"cc_{i}", label_visibility="collapsed")
        minv        = c[2].number_input("", value=to_int(cap.get('MINIMO',1000)),  key=f"cmin_{i}", step=100, min_value=0, label_visibility="collapsed")
        maxv        = c[3].number_input("", value=to_int(cap.get('MAXIMO',1100)),  key=f"cmax_{i}", step=100, min_value=1, label_visibility="collapsed")
        lotes       = c[4].number_input("", value=to_int(cap.get('LOTES',5)),      key=f"cl_{i}",  step=1,   min_value=1, label_visibility="collapsed")
        semanas     = c[5].number_input("", value=to_int(cap.get('SEMANAS',4)),    key=f"cs_{i}",  step=1,   min_value=1, label_visibility="collapsed")
        cap_calc    = lotes * DIAS_SEMANA * semanas * maxv
        c[6].markdown(f"<div style='padding-top:6px'><span class='badge badge-blue'>{cap_calc:,}</span></div>", unsafe_allow_html=True)
        min_ancho   = c[7].number_input("", value=to_int(cap.get('MIN_ANCHO',1)),  key=f"cma_{i}", step=1,   min_value=1, label_visibility="collapsed")
        max_ancho   = c[8].number_input("", value=to_int(cap.get('MAX_ANCHO',4)),  key=f"cmxa_{i}",step=1,   min_value=1, label_visibility="collapsed")
        ctd_anchos  = c[9].number_input("", value=to_int(cap.get('CTDMAXANCHOS',3)),key=f"cca_{i}",step=1,  min_value=1, max_value=10, label_visibility="collapsed")
        mix_sel     = c[10].selectbox("", mix_options,  index=safe_mix_index(cap.get('MIX','DYE'), mix_options),         key=f"cmix_{i}", label_visibility="collapsed")
        tipo_sel    = c[11].selectbox("", tipo_options, index=safe_str_index(cap.get('TIPO_TEJIDO','TODOS'), tipo_options), key=f"ctj_{i}",  label_visibility="collapsed")

        updated.append({
            "CATEGORIA": cat, "MINIMO": minv, "MAXIMO": maxv,
            "LOTES": lotes, "SEMANAS": semanas,
            "MIN_ANCHO": min_ancho, "MAX_ANCHO": max_ancho,
            "CTDMAXANCHOS": ctd_anchos, "MIX": mix_sel,
            "TIPO_TEJIDO": tipo_sel, "ACTIVO": activo_new,
            "CAPACIDAD_LBS": cap_calc,
        })

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Agregar Categoría"):
        updated.append({"CATEGORIA":"NUEVA","MINIMO":1000,"MAXIMO":1100,"LOTES":5,"SEMANAS":4,
                        "MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"DYE",
                        "TIPO_TEJIDO":"TODOS","ACTIVO":True,"CAPACIDAD_LBS":0})

    st.session_state['capacidades'] = updated

# ─── TAB 2: RESTRICCIONES ───────────────────────────────────────────────────────
def rest_table(data, col_defs, prefix):
    """Generic editable restriction table. col_defs: list of (name, 'text'|'int'|'int_opt')."""
    headers = [""] + [cd[0] for cd in col_defs] + [""]
    hc = st.columns([0.3] + [1]*len(col_defs) + [0.25])
    for col, lbl in zip(hc, headers):
        col.markdown(f"<div class='col-header'>{lbl}</div>", unsafe_allow_html=True)

    updated = []
    to_delete = set()

    for i, row in enumerate(data):
        c = st.columns([0.3] + [1]*len(col_defs) + [0.25])
        activo = c[0].checkbox("", value=bool(row.get('ACTIVO', True)), key=f"{prefix}_act_{i}")
        vals   = {"ACTIVO": activo}
        for j, (name, kind) in enumerate(col_defs):
            raw = row.get(name, None)
            if kind == 'text':
                vals[name] = c[j+1].text_input("", value=str(raw) if raw else "", key=f"{prefix}_{name}_{i}", label_visibility="collapsed")
            elif kind == 'int':
                vals[name] = c[j+1].number_input("", value=to_int(raw, 18), key=f"{prefix}_{name}_{i}", step=1, min_value=0, label_visibility="collapsed")
            elif kind == 'int_opt':
                txt = c[j+1].text_input("", value=str(to_int(raw)) if raw is not None else "", key=f"{prefix}_{name}_{i}", label_visibility="collapsed", placeholder="—")
                vals[name] = to_int(txt) if txt.strip().isdigit() else None
        if c[-1].button("✕", key=f"{prefix}_del_{i}"):
            to_delete.add(i)
        else:
            updated.append(vals)

    if st.button("➕ Agregar fila", key=f"{prefix}_add"):
        new = {name: ('' if kind=='text' else (0 if kind=='int' else None)) for name, kind in col_defs}
        new['ACTIVO'] = True
        updated.append(new)

    return updated

def tab_restricciones():
    st.markdown("### Restricciones de Asignación")
    t1, t2, t3, t4 = st.tabs(["🔩 Ancho","🎨 Color","👕 Familia","📐 Anchos Combinados"])

    with t1:
        st.caption("STYLEs con restricción de ancho máximo y categoría destino (lbs)")
        data = st.session_state.get('rest_ancho', DEFAULT_RESTRICCIONES_ANCHO)
        col_defs = [("STYLE","text"),("LIMITE_ANCHO","int"),("PRIORIDAD_1","int_opt"),("PRIORIDAD_2","int_opt"),("PRIORIDAD_3","int_opt")]
        st.session_state['rest_ancho'] = rest_table(data, col_defs, "ra")

    with t2:
        st.caption("Colores con restricción de categoría destino")
        data = st.session_state.get('rest_color', DEFAULT_RESTRICCIONES_COLOR)
        col_defs = [("COLOR_R","text"),("PRIORIDAD_1","int_opt"),("PRIORIDAD_2","int_opt"),("PRIORIDAD_3","int_opt")]
        st.session_state['rest_color'] = rest_table(data, col_defs, "rc")

    with t3:
        st.caption("Familias con restricción de categoría destino")
        data = st.session_state.get('rest_familia', DEFAULT_RESTRICCIONES_FAMILIA)
        col_defs = [("FAMILIA","text"),("PRIORIDAD_1","int_opt"),("PRIORIDAD_2","int_opt"),("PRIORIDAD_3","int_opt"),("PRIORIDAD_4","int_opt")]
        st.session_state['rest_familia'] = rest_table(data, col_defs, "rf")

    with t4:
        st.caption("Si un lote combina ANCHO_1 y ANCHO_2, dirigirlo a estas capacidades")
        data = st.session_state.get('anchos_combinados', [])
        col_defs = [("ANCHO_1","int"),("ANCHO_2","int"),("CAPACIDAD_PRIORIDAD_1","int_opt"),("CAPACIDAD_PRIORIDAD_2","int_opt"),("CAPACIDAD_PRIORIDAD_3","int_opt")]
        st.session_state['anchos_combinados'] = rest_table(data, col_defs, "ac")

# ─── TAB 3: CONFIGURACIÓN ───────────────────────────────────────────────────────
def tab_config():
    st.markdown("### Configuración Avanzada del Solver")
    cfg = st.session_state.get('config', DEFAULT_CONFIG)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='elc-card'>", unsafe_allow_html=True)
        st.markdown("**🔧 Parámetros del Solver**")
        max_items = st.number_input("MAX_ITEMS — máx. SKUs por lote",
                                    value=to_int(cfg.get('MAX_ITEMS',8)),
                                    min_value=2, max_value=30, step=1,
                                    help="Máximo de ítems en un lote")
        timeout   = st.number_input("Tiempo límite solver (segundos)",
                                    value=to_int(cfg.get('SOLVER_TIMEOUT',5)),
                                    min_value=1, max_value=120, step=1)
        bleach    = st.checkbox("Aplicar reglas especiales BLEACH",
                                value=bool(cfg.get('APPLY_RULES_BLEACH', False)))
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='elc-card'>", unsafe_allow_html=True)
        st.markdown("**🔀 Combinación de Prioridades**")
        st.caption("Pares de prioridades que pueden mezclarse en un mismo lote (un par por línea, separados por coma)")
        combo_default = cfg.get('COMBINACION_PRIORIDAD', [["VENCIDOS","AHEAD"],["AHEAD","AHEAD2"],["AHEAD2","OTROS"]])
        combo_txt = st.text_area("", value="\n".join([",".join(p) for p in combo_default]),
                                 height=120, label_visibility="collapsed")
        try:
            combo_parsed = [ln.strip().split(",") for ln in combo_txt.strip().split("\n") if "," in ln]
        except Exception:
            combo_parsed = combo_default
        st.markdown("</div>", unsafe_allow_html=True)

    st.session_state['config'] = {
        "MAX_ITEMS": max_items,
        "SOLVER_TIMEOUT": timeout,
        "APPLY_RULES_BLEACH": bleach,
        "COMBINACION_PRIORIDAD": combo_parsed,
    }

# ─── TAB 4: EJECUTAR ────────────────────────────────────────────────────────────
def tab_ejecutar():
    st.markdown("### Cargar Datos y Ejecutar Loteador")

    uploaded = st.file_uploader(
        "📂 Sube el archivo Excel (requiere hoja **DATA** con header en fila 3)",
        type=["xlsx"]
    )

    if uploaded:
        file_bytes      = uploaded.read()
        df_raw, err     = read_excel_data(file_bytes)
        if err:
            st.error(err)
            return

        df = build_join_from_data(df_raw)
        if df is None:
            return

        st.session_state['df_cargado'] = df

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-box'><div class='metric-val'>{len(df):,}</div><div class='metric-lbl'>Registros</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'><div class='metric-val'>{df['COLOR_A'].nunique():,}</div><div class='metric-lbl'>Colores</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'><div class='metric-val'>{df['MIX'].nunique()}</div><div class='metric-lbl'>Tipos MIX</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-box'><div class='metric-val'>{df['LBS_C'].sum():,.0f}</div><div class='metric-lbl'>Total LBS</div></div>", unsafe_allow_html=True)

        with st.expander("👁 Vista previa de datos (primeras 30 filas)"):
            show_cols = [c for c in ['COLOR_A','ESTILO_C','ANCHO','LBS_C','MIX','TIPO_TEJIDO','PCT_CARGA','COLOR_R','FAMILIA','PRIORIDAD'] if c in df.columns]
            st.dataframe(df[show_cols].head(30), use_container_width=True, height=240)

    st.markdown("---")
    caps_activas = [c for c in st.session_state.get('capacidades', DEFAULT_CAPACIDADES) if c.get('ACTIVO', True)]
    st.caption(f"Se procesarán **{len(caps_activas)}** categorías activas con los parámetros configurados.")

    if st.button("▶  EJECUTAR LOTEADOR", use_container_width=False):
        df = st.session_state.get('df_cargado', None)
        if df is None:
            st.warning("⚠ Primero sube un archivo Excel.")
            return

        GLOBAL_TIMEOUT = 600  # 10 minutos máximo total

        result_holder = [None]
        error_holder  = [None]

        def _run():
            try:
                result_holder[0] = run_all(
                    df,
                    st.session_state.get('capacidades', DEFAULT_CAPACIDADES),
                    st.session_state.get('config',      DEFAULT_CONFIG),
                )
            except Exception as e:
                error_holder[0] = str(e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        spinner_msgs = [
            "Agrupando por COLOR_A…",
            "Resolviendo subproblemas…",
            "Optimizando lotes…",
            "Casi listo…",
        ]
        start = time.time()
        msg_idx = 0
        progress_bar = st.progress(0)
        status_msg   = st.empty()

        while t.is_alive():
            elapsed = time.time() - start
            if elapsed > GLOBAL_TIMEOUT:
                st.error("⏱ Tiempo límite global alcanzado (10 min). Reduce el número de filas o aumenta el timeout por lote.")
                break
            pct = min(int(elapsed / GLOBAL_TIMEOUT * 100), 95)
            progress_bar.progress(pct)
            status_msg.markdown(
                f"<small>⚙ {spinner_msgs[msg_idx % len(spinner_msgs)]} — <b>{int(elapsed)}s</b> transcurridos</small>",
                unsafe_allow_html=True
            )
            msg_idx += 1
            time.sleep(2)
            t.join(timeout=0)

        progress_bar.empty()
        status_msg.empty()

        if error_holder[0]:
            st.error(f"Error en el solver: {error_holder[0]}")
        elif result_holder[0] is None or (hasattr(result_holder[0], 'empty') and result_holder[0].empty):
            st.warning("No se generaron lotes. Revisa parámetros y datos.")
        else:
            result = result_holder[0]
            st.session_state['resultado'] = result
            n_lotes = result['LOTE_ID'].nunique()
            elapsed = round(time.time() - start, 1)
            st.success(f"✅ Completado en {elapsed}s: **{n_lotes} lotes** generados con **{len(result)} registros**. Ve a **Resultados**.")

# ─── TAB 5: RESULTADOS ──────────────────────────────────────────────────────────
def tab_resultados():
    st.markdown("### Resultados del Loteador")

    result = st.session_state.get('resultado', None)
    if result is None:
        st.info("Aún no hay resultados. Ve a **▶ Ejecutar** para correr el loteador.")
        return

    n_lotes   = result['LOTE_ID'].nunique()
    total_lbs = result.groupby('LOTE_ID')['TOTAL_LOTE'].first().sum()
    cats_n    = result['CATEGORIA'].nunique()
    puro_n    = result[result['TIPO_LOTE_ANCHO']=='PURO']['LOTE_ID'].nunique()
    puro_pct  = round(puro_n / n_lotes * 100, 1) if n_lotes else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='metric-box'><div class='metric-val'>{n_lotes}</div><div class='metric-lbl'>Lotes Generados</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-box'><div class='metric-val'>{total_lbs:,.0f}</div><div class='metric-lbl'>Total LBS Loteadas</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-box'><div class='metric-val'>{cats_n}</div><div class='metric-lbl'>Categorías Usadas</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-box'><div class='metric-val'>{puro_pct}%</div><div class='metric-lbl'>% Lotes Puros</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        cat_f = st.selectbox("Categoría", ["Todas"] + sorted(result['CATEGORIA'].unique().tolist()))
    with cf2:
        tipo_f = st.selectbox("Tipo Lote", ["Todos"] + sorted(result['TIPO_LOTE_ANCHO'].dropna().unique().tolist()))
    with cf3:
        mix_f = st.selectbox("MIX", ["Todos"] + sorted(result['MIX'].dropna().unique().tolist()))

    df_show = result.copy()
    if cat_f  != "Todas": df_show = df_show[df_show['CATEGORIA']       == cat_f]
    if tipo_f != "Todos": df_show = df_show[df_show['TIPO_LOTE_ANCHO'] == tipo_f]
    if mix_f  != "Todos": df_show = df_show[df_show['MIX']             == mix_f]

    st.dataframe(df_show, use_container_width=True, height=400)

    with st.expander("📊 Resumen por Categoría"):
        resumen = (result.groupby('CATEGORIA')
                   .agg(Lotes=('LOTE_ID','nunique'),
                        Registros=('LOTE_ID','count'),
                        LBS_Total=('LBS_C','sum'),
                        Puros=('TIPO_LOTE_ANCHO', lambda x: (x=='PURO').sum()),
                        MixControlado=('TIPO_LOTE_ANCHO', lambda x: (x=='MIX_CONTROLADO').sum()),
                        MixAlto=('TIPO_LOTE_ANCHO', lambda x: (x=='MIX_ALTO').sum()))
                   .reset_index())
        st.dataframe(resumen, use_container_width=True)

    st.markdown("---")
    tz    = pytz.timezone("America/Tegucigalpa")
    ts    = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    fname = f"loteo_OPTIMO_{ts}.xlsx"
    buf   = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        result.to_excel(writer, sheet_name='LOTES', index=False)
        resumen.to_excel(writer, sheet_name='RESUMEN', index=False)
    buf.seek(0)
    st.download_button("⬇ Descargar Excel", data=buf, file_name=fname,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ─── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    sidebar()

    st.markdown("""
    <div class="logo-header">
      <div style="font-size:18px;font-weight:800;color:white;letter-spacing:0.5px;">🏭 Loteador Óptimo de Tintorería</div>
      <div style="font-size:9px;color:#cce4ff;letter-spacing:2px;text-transform:uppercase;margin-top:3px;">Grupo Elcatex · Optimización OR-Tools · Honduras 🇭🇳</div>
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
