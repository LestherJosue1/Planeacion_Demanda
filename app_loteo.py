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
    {"CATEGORIA":"A-4000","MINIMO":3900,"MAXIMO":4000,"LOTES":5, "SEMANAS":4.0,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":4,"MIX":"DYE",   "TIPO_TEJIDO":"FLEECE","ACTIVO":True},
    {"CATEGORIA":"B-3300","MINIMO":3000,"MAXIMO":3300,"LOTES":6, "SEMANAS":4.0,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":4,"MIX":"DYE",   "TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"C-2600","MINIMO":2500,"MAXIMO":2600,"LOTES":29,"SEMANAS":4.0,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"DYE",   "TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"D-2200","MINIMO":2000,"MAXIMO":2200,"LOTES":17,"SEMANAS":4.0,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"DYE",   "TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"E-1100","MINIMO":1000,"MAXIMO":1100,"LOTES":25,"SEMANAS":4.0,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":2,"MIX":"DYE",   "TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"F-2200","MINIMO":2000,"MAXIMO":2200,"LOTES":21,"SEMANAS":4.0,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":3,"MIX":"BLEACH","TIPO_TEJIDO":"TODOS", "ACTIVO":True},
    {"CATEGORIA":"G-1100","MINIMO":1000,"MAXIMO":1100,"LOTES":4, "SEMANAS":4.0,"MIN_ANCHO":1,"MAX_ANCHO":4,"CTDMAXANCHOS":2,"MIX":"BLEACH","TIPO_TEJIDO":"TODOS", "ACTIVO":True},
]

DEFAULT_CONFIG = {
    "MAX_ITEMS": 8,
    "SOLVER_TIMEOUT": 5,
    "COMBINACION_PRIORIDAD": [["VENCIDOS","AHEAD"],["AHEAD","AHEAD2"],["AHEAD2","OTROS"]],
    "APPLY_RULES_BLEACH": False,
}

DEFAULT_RESTRICCIONES_ANCHO = [
    {"STYLE":"PC54Y",   "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC55LS",  "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC55Y",   "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC330Y",  "LIMITE_ANCHO":18,"PRIORIDAD_1":2200,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC54-2",  "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC55-2",  "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC54LS",  "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC61Y",   "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC54DTG", "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"LPC61",   "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC55P",   "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
    {"STYLE":"PC61LSP", "LIMITE_ANCHO":18,"PRIORIDAD_1":2600,"PRIORIDAD_2":None,"PRIORIDAD_3":None,"ACTIVO":True},
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

    # Preservar columnas extra para reportes (LNK, TONO, CONSUMO_C, STYLE, BD)
    for col_orig, col_dest in [('BD','LNK'), ('LNK','LNK'), ('TONO','TONO'),
                                ('CONSUMO_C','CONSUMO_C'), ('STYLE','STYLE'),
                                ('PLANTA_COSTURA','PLANTA'), ('PRIORIDAD','PRIORIDAD')]:
        if col_orig in df.columns and col_dest not in df.columns:
            df[col_dest] = df[col_orig]
        elif col_orig in df.columns:
            df[col_dest] = df[col_orig]

    # LNK_PRIORIDAD = LNK|PRIORIDAD para trazabilidad
    if 'LNK' in df.columns and 'PRIORIDAD' in df.columns:
        df['LNK_PRIORIDAD'] = df['LNK'].astype(str) + '|' + df['PRIORIDAD'].astype(str)

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
    """Retorna dict de parametros — se aplican directamente al solver.parameters."""
    return {
        "max_time_in_seconds": float(timeout),
        "num_search_workers":  1,
        "cp_model_presolve":   True,
        "log_search_progress": False,
    }

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

def _solve_one_group_no_tela(grupo, idxs_disp, usados, min_lbs, max_lbs, max_anchos, max_items, solver_params):
    """
    Resuelve un subproblema para los índices disponibles dentro de un grupo COLOR_A.
    SIN regla de incompatibilidad de telas — la compatibilidad está garantizada
    por el agrupamiento por COLOR_A (mismo baño de tinte = mismas condiciones).
    Retorna (indices_seleccionados, suma_lbs) o ([], 0) si no hay solución.
    """
    disponibles = [i for i in idxs_disp if i not in usados]
    if len(disponibles) < 1:
        return [], 0

    # Pre-filtro: descartar ítems que exceden el máximo individualmente
    disponibles = [i for i in disponibles if grupo.loc[i,'LBS_C'] <= max_lbs]
    if len(disponibles) < 1:
        return [], 0

    # Si hay un solo ítem y cae dentro del rango, lo asignamos directamente
    if len(disponibles) == 1:
        i    = disponibles[0]
        lbs  = grupo.loc[i,'LBS_C']
        if min_lbs <= lbs <= max_lbs:
            return [i], lbs
        return [], 0

    model = cp_model.CpModel()
    x     = {i: model.NewBoolVar(f"x{i}") for i in disponibles}

    lbs_vals = [int(grupo.loc[i,'LBS_C']) for i in disponibles]
    lbs_expr = sum(v * x[i] for v, i in zip(lbs_vals, disponibles))

    model.Add(lbs_expr >= int(min_lbs))
    model.Add(lbs_expr <= int(max_lbs))
    model.Add(sum(x[i] for i in disponibles) <= int(max_items))

    # Control de anchos únicos en el lote
    anchos_unicos = list(set().union(*grupo.loc[disponibles,'ANCHOS_SET']))
    y = {a: model.NewBoolVar(f"y{a}") for a in anchos_unicos}
    for i in disponibles:
        for a in grupo.loc[i,'ANCHOS_SET']:
            model.Add(x[i] <= y[a])
    model.Add(sum(y[a] for a in anchos_unicos) <= int(max_anchos))

    model.Maximize(lbs_expr)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = solver_params["max_time_in_seconds"]
    solver.parameters.num_search_workers  = solver_params["num_search_workers"]
    solver.parameters.cp_model_presolve   = solver_params["cp_model_presolve"]
    solver.parameters.log_search_progress = solver_params["log_search_progress"]
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return [], 0

    sel  = [i for i in disponibles if solver.Value(x[i]) == 1]
    suma = sum(grupo.loc[i,'LBS_C'] for i in sel)

    if len(sel) < 1 or suma < min_lbs:
        return [], 0

    return sel, suma


# kept for compatibility (not used)
def _solve_one_group(grupo, idxs_disp, usados, min_lbs, max_lbs, max_anchos, max_items, solver_params):
    return _solve_one_group_no_tela(grupo, idxs_disp, usados, min_lbs, max_lbs, max_anchos, max_items, solver_params)


def run_loteador(df_cat, cap, max_items, solver_timeout):
    """
    Loteador con SPLIT de cortes grandes.
    Cuando un corte tiene mas LBS de las que caben en un lote, se divide en partes
    proporcionales — igual que el Colab. Esto es lo que permite llegar al 90%+.
    """
    min_lbs    = to_int(cap['MINIMO'])
    max_lbs    = to_int(cap['MAXIMO'])
    mix_tipo   = str(cap['MIX']).upper()
    tipo_tej   = str(cap['TIPO_TEJIDO']).upper()
    max_anchos = to_int(cap['CTDMAXANCHOS'], 3)
    max_lotes  = round(to_int(cap.get('LOTES', 9999)) * DIAS_SEMANA * to_float(cap.get('SEMANAS', 4)))

    # Filtros de categoría
    grupo_cat = df_cat[df_cat['MIX'].str.upper() == mix_tipo].copy()
    if tipo_tej != 'TODOS':
        grupo_cat = grupo_cat[grupo_cat['TIPO_TEJIDO'].str.upper().isin([tipo_tej, 'TODOS'])]
    if grupo_cat.empty:
        return [], grupo_cat

    grupo_cat['ANCHOS_SET'] = grupo_cat['ANCHO'].apply(lambda x: {str(x)})

    # ── APLICAR PCT_CARGA: ajustar LBS efectivas ──────────────────────────────
    # Si un producto tiene PCT_CARGA=0.7 se planifica al 70% de sus LBS
    # pero se identifica en la categoría original
    if 'PCT_CARGA' in grupo_cat.columns:
        grupo_cat['LBS_EFECTIVA'] = (grupo_cat['LBS_C'] * grupo_cat['PCT_CARGA'].clip(0.01, 1.0)).round(0)
    else:
        grupo_cat['LBS_EFECTIVA'] = grupo_cat['LBS_C']

    # ── SPLIT: expandir filas con LBS > max_lbs en fragmentos ─────────────────
    #
    # REGLA DE SPLIT MÍNIMO:
    #   SPLIT_MIN = 500 lbs.
    #   Un LNK solo se parte si sus LBS_EFECTIVA >= 2 * SPLIT_MIN (>=1000 lbs).
    #   Esto garantiza que después de tomar el primer fragmento (>=SPLIT_MIN),
    #   el remanente también sea >= SPLIT_MIN — sin canibalizar la demanda.
    #
    #   Ejemplos:
    #     700 lbs  → NO se parte (quedarían solo 200 lbs, menor que SPLIT_MIN)
    #     1,000 lbs → SÍ: 2 partes de 500 lbs cada una
    #     1,200 lbs → SÍ: parte_1=600, parte_2=600  (o parte_1=500, remanente=700)
    #     2,600 lbs → SÍ: 5 partes de 520 lbs (todas >= SPLIT_MIN)
    #     4,500 lbs → SÍ: 2 partes de 2,250 lbs (dentro del rango min-max de categoría)
    #
    SPLIT_MIN = 500.0

    expanded_rows = []
    for orig_idx, row in grupo_cat.iterrows():
        lbs_total = float(row['LBS_EFECTIVA'])
        if lbs_total <= 0:
            continue

        # ¿Vale la pena partir este LNK?
        if lbs_total < 2 * SPLIT_MIN:
            # LNK demasiado pequeño para partir sin canibalizar — entra entero
            new_row = row.copy()
            new_row['LBS_C']       = round(lbs_total, 1)
            new_row['LBS_EFECTIVA']= round(lbs_total, 1)
            new_row['_orig_idx']   = orig_idx
            new_row['_part']       = 0
            new_row['_split']      = False
            expanded_rows.append(new_row)
            continue

        # Calcular cuántas partes caben, respetando SPLIT_MIN en cada parte
        # Queremos partes lo más grandes posible (cercanas a max_lbs) pero >= SPLIT_MIN
        if lbs_total <= max_lbs:
            # Cabe entero en un lote — no partir
            n_parts = 1
        else:
            # Partir: cuántos lotes necesita?
            # Tomamos ceil(lbs_total / max_lbs) pero verificando que cada parte >= SPLIT_MIN
            import math
            n_parts = math.ceil(lbs_total / max_lbs)
            lbs_per_part_test = lbs_total / n_parts
            # Si alguna parte quedaría < SPLIT_MIN, ajustar
            while lbs_per_part_test < SPLIT_MIN and n_parts > 1:
                n_parts -= 1
                lbs_per_part_test = lbs_total / n_parts

        lbs_per_part = round(lbs_total / n_parts, 1)
        # Ajustar última parte para que el total cuadre exacto
        for part in range(n_parts):
            new_row = row.copy()
            if part == n_parts - 1:
                # Última parte toma el remanente exacto
                asignado = round(lbs_per_part * part, 1)
                lbs_esta_parte = round(lbs_total - asignado, 1)
            else:
                lbs_esta_parte = lbs_per_part
            new_row['LBS_C']       = lbs_esta_parte
            new_row['LBS_EFECTIVA']= lbs_esta_parte
            new_row['_orig_idx']   = orig_idx
            new_row['_part']       = part
            new_row['_split']      = n_parts > 1
            expanded_rows.append(new_row)

    if not expanded_rows:
        return [], grupo_cat

    grupo_exp = pd.DataFrame(expanded_rows).reset_index(drop=True)
    grupo_exp['ANCHOS_SET'] = grupo_exp['ANCHO'].apply(lambda x: {str(x)})

    sparams = _solver_params(solver_timeout)
    lotes   = []
    lid     = 1

    # ── AGRUPACIÓN POR COLOR_A ────────────────────────────────────────────────
    for color, grupo in grupo_exp.groupby('COLOR_A'):
        if len(lotes) >= max_lotes:
            break

        idxs   = _prefilter(grupo, min_lbs, max_lbs, max_items)
        usados = set()

        while True:
            if len(lotes) >= max_lotes:
                break
            sel, suma = _solve_one_group_no_tela(
                grupo, idxs, usados,
                min_lbs, max_lbs, max_anchos, max_items, sparams
            )
            if not sel:
                break
            for i in sel:
                usados.add(i)
            lotes.append((lid, sel, suma))
            lid += 1

    return lotes, grupo_exp



def _format_excel_output(writer):
    """Aplica formato Calibri 8, autofit columnas y formato numérico a todas las hojas."""
    from openpyxl.styles import Font, PatternFill, Alignment, numbers
    from openpyxl.utils import get_column_letter

    wb = writer.book
    header_fill  = PatternFill("solid", fgColor="003876")
    header_font  = Font(name="Calibri", size=8, bold=True, color="FFFFFF")
    cell_font    = Font(name="Calibri", size=8)
    num_fmt      = "#,##0"
    dec_fmt      = "#,##0.0"

    for ws in wb.worksheets:
        col_widths = {}

        for row_idx, row in enumerate(ws.iter_rows()):
            for cell in row:
                # Font
                if row_idx == 0:
                    cell.font      = header_font
                    cell.fill      = header_fill
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
                else:
                    cell.font      = cell_font
                    cell.alignment = Alignment(vertical="center")
                    # Numeric format
                    if cell.value is not None and isinstance(cell.value, (int, float)):
                        # Decide dec or int
                        col_letter = get_column_letter(cell.column)
                        header_val = ws.cell(1, cell.column).value or ""
                        if any(x in str(header_val).upper() for x in ["PCT","FILL","CARGA","SEMANA","%"]):
                            cell.number_format = dec_fmt
                        else:
                            cell.number_format = num_fmt

                # Autofit width tracking
                col_letter = get_column_letter(cell.column)
                val_len = len(str(cell.value)) if cell.value is not None else 0
                col_widths[col_letter] = max(col_widths.get(col_letter, 8), min(val_len + 2, 35))

        for col_letter, width in col_widths.items():
            ws.column_dimensions[col_letter].width = width

        # Freeze top row
        ws.freeze_panes = "A2"

def _build_reports(result, df_original, capacidades):
    """Construye todas las hojas del reporte Excel — estructura identica al output de Colab."""

    cat_max = {c['CATEGORIA']: to_int(c['MAXIMO']) for c in capacidades}
    cat_min = {c['CATEGORIA']: to_int(c['MINIMO']) for c in capacidades}

    # ── DETALLE_LOTES — igual columnas que Colab ─────────────────────────────
    # Columnas Colab: LOTE_ID, ANCHOS_LOTE, CATEGORIA, MIX, TELA.CUERPO, COLOR,
    #   TONO, LNK, PRIORIDAD, BLOQUE, ANCHO.F.C, CONSUMO_C, FAMILIA, COLOR_R,
    #   STYLE, LBS_ASIGNADAS, APLICA_REGLA, PRIORIDAD_USADA, DOCENAS
    det = result.copy()
    det = det.rename(columns={
        'SET_ANCHOS_LOTE': 'ANCHOS_LOTE',
        'ESTILO_C':        'TELA.CUERPO',
        'COLOR_A':         'COLOR',
        'LBS_C':           'LBS_ASIGNADAS',
        'ANCHO':           'ANCHO.F.C',
    })
    # Columnas derivadas que el Colab calculaba
    det['BLOQUE']          = det.get('PRIORIDAD', '')  # en data no hay BLOQUE separado
    det['APLICA_REGLA']    = 'NONE'
    det['PRIORIDAD_USADA'] = det['CATEGORIA'].map(cat_max)
    if 'CONSUMO_C' in det.columns:
        det['DOCENAS'] = (det['LBS_ASIGNADAS'] / det['CONSUMO_C'].replace(0, float('nan'))).round(2)
        det['DOCENAS'] = det['DOCENAS'].fillna(0)
    else:
        det['DOCENAS'] = 0
    det['LBS_EXTRA_SOBRE_ORDEN'] = 0

    det_cols = [c for c in [
        'LOTE_ID','ANCHOS_LOTE','CATEGORIA','MIX','TELA.CUERPO','COLOR',
        'TONO','LNK','PRIORIDAD','BLOQUE','ANCHO.F.C','CONSUMO_C',
        'FAMILIA','COLOR_R','STYLE','LBS_ASIGNADAS','LBS_EXTRA_SOBRE_ORDEN',
        'APLICA_REGLA','PRIORIDAD_USADA','DOCENAS','TIPO_TEJIDO','PCT_CARGA',
        'TOTAL_LOTE','PCT_CARGA_REAL','CANT_ANCHOS','TIPO_LOTE_ANCHO'
    ] if c in det.columns]
    detalle = det[det_cols].copy()

    # ── RESUMEN_LOTES — igual columnas que Colab ─────────────────────────────
    # Colab: LOTE_ID, ANCHOS_LOTE, CATEGORIA, MIX, TELA.CUERPO, COLOR/TONO_KEY,
    #   LBS_TOTAL, MIN_RANGO, MAX_RANGO, CAPACIDAD_PERDIDA, SKU_DISTINTOS,
    #   ANCHOS_UNICOS, BLOQUE_DOMINANTE, REGLA_DOMINANTE, PRIORIDAD_FINAL,
    #   COMBO_ANCHOS, STYLE_CRITICO, CANT_REGLAS_APLICADAS, UPGRADE_CATEGORIA
    res_grp = result.groupby(['LOTE_ID','SET_ANCHOS_LOTE','CATEGORIA','MIX'])
    resumen = res_grp.agg(
        TELA_CUERPO      = ('ESTILO_C',  lambda x: x.iloc[0]),
        COLOR_TONO_KEY   = ('COLOR_A',   lambda x: '|'.join(sorted(x.unique()))),
        LBS_TOTAL        = ('TOTAL_LOTE','first'),
        MIN_RANGO        = ('CATEGORIA', lambda x: cat_min.get(x.iloc[0], 0)),
        MAX_RANGO        = ('CATEGORIA', lambda x: cat_max.get(x.iloc[0], 0)),
        SKU_DISTINTOS    = ('ANCHO',     'count'),
        ANCHOS_UNICOS    = ('CANT_ANCHOS','first'),
        BLOQUE_DOMINANTE = ('PRIORIDAD', lambda x: x.mode()[0] if len(x) else ''),
        PRIORIDAD_FINAL  = ('CATEGORIA', lambda x: cat_max.get(x.iloc[0], 0)),
        TIPO_LOTE        = ('TIPO_LOTE_ANCHO','first'),
    ).reset_index().rename(columns={
        'SET_ANCHOS_LOTE':'ANCHOS_LOTE',
        'TELA_CUERPO':    'TELA.CUERPO',
        'COLOR_TONO_KEY': 'COLOR/TONO_KEY',
    })
    resumen['CAPACIDAD_PERDIDA']    = resumen.apply(lambda r: max(0, cat_max.get(r['CATEGORIA'],0) - r['LBS_TOTAL']), axis=1)
    resumen['REGLA_DOMINANTE']      = 'NONE'
    resumen['COMBO_ANCHOS']         = resumen['ANCHOS_UNICOS'] > 1
    resumen['STYLE_CRITICO']        = False
    resumen['CANT_REGLAS_APLICADAS']= 0
    resumen['UPGRADE_CATEGORIA']    = 1
    col_order = ['LOTE_ID','ANCHOS_LOTE','CATEGORIA','MIX','TELA.CUERPO','COLOR/TONO_KEY',
                 'LBS_TOTAL','MIN_RANGO','MAX_RANGO','CAPACIDAD_PERDIDA','SKU_DISTINTOS',
                 'ANCHOS_UNICOS','BLOQUE_DOMINANTE','REGLA_DOMINANTE','PRIORIDAD_FINAL',
                 'COMBO_ANCHOS','STYLE_CRITICO','CANT_REGLAS_APLICADAS','UPGRADE_CATEGORIA','TIPO_LOTE']
    resumen = resumen[[c for c in col_order if c in resumen.columns]]

    # ── EXCEDENTES — igual columnas que Colab ────────────────────────────────
    # Colab: LNK, TELA.CUERPO, COLOR, TONO, MIX, PRIORIDAD, BLOQUE,
    #        ANCHO.F.C, ANCHO.F.M, TOTAL, LBS_RESTANTES, LBS_SCRAP
    assigned_idx = set(result.index)
    exc_raw = df_original[~df_original.index.isin(assigned_idx)].copy()
    if not exc_raw.empty:
        exc_raw = exc_raw.rename(columns={
            'COLOR_A':   'COLOR',
            'ESTILO_C':  'TELA.CUERPO',
            'LBS_C':     'LBS_RESTANTES',
            'ANCHO':     'ANCHO.F.C',
        })
        exc_raw['LBS_SCRAP'] = 0
        exc_raw['ANCHO.F.M'] = 0
        exc_raw['BLOQUE']    = exc_raw.get('PRIORIDAD', '')
        exc_raw['TOTAL']     = exc_raw['LBS_RESTANTES']
        exc_cols = [c for c in ['LNK','TELA.CUERPO','COLOR','TONO','MIX','PRIORIDAD',
                                 'BLOQUE','ANCHO.F.C','ANCHO.F.M','TOTAL','LBS_RESTANTES','LBS_SCRAP'] if c in exc_raw.columns]
        excedentes = exc_raw[exc_cols]
    else:
        excedentes = pd.DataFrame(columns=['LNK','TELA.CUERPO','COLOR','TONO','MIX',
                                            'PRIORIDAD','BLOQUE','ANCHO.F.C','ANCHO.F.M',
                                            'TOTAL','LBS_RESTANTES','LBS_SCRAP'])

    # ── CAPACIDAD_X_CATEG — LBS_ASIGNADAS = suma de TOTAL_LOTE (un valor por lote) ──
    # FIX: usar first() de TOTAL_LOTE por lote, no suma de filas individuales
    lbs_x_cat = (result.groupby(['CATEGORIA','LOTE_ID'])['TOTAL_LOTE']
                 .first()
                 .reset_index()
                 .groupby('CATEGORIA')['TOTAL_LOTE']
                 .sum()
                 .reset_index())
    lbs_x_cat.columns = ['CATEGORIA','LBS_ASIGNADAS']

    cap_rows = []
    for c in capacidades:
        cat     = c['CATEGORIA']
        mix     = c['MIX']
        minv    = to_int(c['MINIMO'])
        maxv    = to_int(c['MAXIMO'])
        lotes_n = to_int(c['LOTES'])
        semanas = to_float(c.get('SEMANAS', 4))
        cap_lbs = round(lotes_n * DIAS_SEMANA * semanas * maxv, 0)
        asig    = float(lbs_x_cat[lbs_x_cat['CATEGORIA']==cat]['LBS_ASIGNADAS'].sum())
        n_lotes = int(result[result['CATEGORIA']==cat]['LOTE_ID'].nunique()) if cat in result['CATEGORIA'].values else 0
        cap_rows.append({
            'CATEGORIA': cat, 'MIX': mix, 'MINIMO': minv, 'MAXIMO': maxv,
            'LOTES_DIA': lotes_n, 'SEMANAS': semanas,
            'MAX_LOTES_PERIODO': int(lotes_n * DIAS_SEMANA * semanas),
            'LOTES_GENERADOS': n_lotes,
            'CAPACIDAD_LBS': cap_lbs,
            'LBS_ASIGNADAS': round(asig, 1),
            'DIFERENCIA': round(cap_lbs - asig, 1),
            'PCT_OCUPACION': round(asig / cap_lbs * 100, 1) if cap_lbs > 0 else 0,
            'ACTIVO': c.get('ACTIVO', True),
        })
    cap_df = pd.DataFrame(cap_rows)

    # ── PRIORIDAD_VS_ASIG — igual que Colab ──────────────────────────────────
    # Colab: MIX, BLOQUE, LBS_BASE, LBS_ASIGNADAS, LBS_SIN_ASIGNAR
    if 'PRIORIDAD' in result.columns:
        prio_asig = (result.groupby(['MIX','PRIORIDAD'])
                     .agg(LBS_ASIGNADAS=('LBS_C','sum'))
                     .reset_index()
                     .rename(columns={'PRIORIDAD':'BLOQUE'}))
        if 'PRIORIDAD' in df_original.columns:
            prio_base = (df_original.groupby(['MIX','PRIORIDAD'])
                         .agg(LBS_BASE=('LBS_C','sum'))
                         .reset_index()
                         .rename(columns={'PRIORIDAD':'BLOQUE'}))
            prio_df = prio_base.merge(prio_asig, on=['MIX','BLOQUE'], how='left').fillna(0)
        else:
            prio_df = prio_asig.copy()
            prio_df['LBS_BASE'] = prio_df['LBS_ASIGNADAS']
        prio_df['LBS_SIN_ASIGNAR'] = prio_df['LBS_BASE'] - prio_df['LBS_ASIGNADAS']
        prio_df = prio_df[['MIX','BLOQUE','LBS_BASE','LBS_ASIGNADAS','LBS_SIN_ASIGNAR']]
    else:
        prio_df = pd.DataFrame(columns=['MIX','BLOQUE','LBS_BASE','LBS_ASIGNADAS','LBS_SIN_ASIGNAR'])

    # ── LNK_COMPLETITUD — igual que Colab ────────────────────────────────────
    # Colab: MIX, LNK, LBS_BASE, LBS_ASIGNADAS, LBS_SCRAP, BALANCE, ESTADO
    lnk_col = next((c for c in ['LNK','SKU','CUT-TICKET'] if c in df_original.columns), None)
    if lnk_col:
        # LBS_BASE = libras originales del cut (antes de lotear)
        lnk_base = (df_original.groupby(lnk_col)
                    .agg(LBS_BASE=('LBS_C','sum'))
                    .reset_index())
        # MIX and PRIORIDAD per LNK
        lnk_meta = df_original[[lnk_col,'MIX']].drop_duplicates(subset=[lnk_col])

        if lnk_col in result.columns:
            # Deduplicar por índice original para evitar doble conteo entre categorías
            result_dedup = result.drop_duplicates(subset=[lnk_col, 'ANCHO', 'LBS_C'])
            lnk_asig = (result_dedup.groupby(lnk_col)
                        .agg(LBS_ASIGNADAS=('LBS_C','sum'))
                        .reset_index())
            lnk_comp = lnk_base.merge(lnk_asig, on=lnk_col, how='left').fillna(0)
        else:
            lnk_comp = lnk_base.copy()
            lnk_comp['LBS_ASIGNADAS'] = 0

        lnk_comp = lnk_comp.merge(lnk_meta, on=lnk_col, how='left')
        lnk_comp['LBS_SCRAP'] = 0
        lnk_comp['BALANCE']   = lnk_comp['LBS_BASE'] - lnk_comp['LBS_ASIGNADAS']
        lnk_comp['ESTADO']    = lnk_comp['BALANCE'].apply(
            lambda b: 'COMPLETO' if abs(b) < 1 else ('PARCIAL' if b > 0 else 'EXCEDIDO'))
        lnk_comp = lnk_comp[['MIX', lnk_col, 'LBS_BASE','LBS_ASIGNADAS','LBS_SCRAP','BALANCE','ESTADO']]
        lnk_comp = lnk_comp.sort_values(['MIX', lnk_col]).reset_index(drop=True)
    else:
        lnk_comp = pd.DataFrame(columns=['MIX','LNK','LBS_BASE','LBS_ASIGNADAS','LBS_SCRAP','BALANCE','ESTADO'])

    # ── REPORTE_REGLAS_MIX ───────────────────────────────────────────────────
    reglas_mix = (result.groupby(['LOTE_ID','SET_ANCHOS_LOTE','MIX','CATEGORIA'])
                  .agg(LBS_TOTAL     =('TOTAL_LOTE','first'),
                       ANCHOS_UNICOS =('CANT_ANCHOS','first'),
                       TIPO_LOTE     =('TIPO_LOTE_ANCHO','first'),
                       SKU_DISTINTOS =('ANCHO','count'),
                       BLOQUE        =('PRIORIDAD', lambda x: x.mode()[0] if len(x) else ''))
                  .reset_index()
                  .rename(columns={'SET_ANCHOS_LOTE':'ANCHOS_LOTE'}))
    reglas_mix['CAPACIDAD_PERDIDA']    = reglas_mix.apply(lambda r: max(0, cat_max.get(r['CATEGORIA'],0) - r['LBS_TOTAL']), axis=1)
    reglas_mix['REGLA_DOMINANTE']      = 'NONE'
    reglas_mix['CANT_REGLAS_APLICADAS']= 0
    reglas_mix['UPGRADE_CATEGORIA']    = 1

    # ── OVERSHOOT_SUMMARY — LNK con LBS_ASIGNADAS > LBS_BASE ────────────────
    if not lnk_comp.empty and 'BALANCE' in lnk_comp.columns:
        overshoot = lnk_comp[lnk_comp['BALANCE'] < 0].copy()
        overshoot = overshoot.rename(columns={'BALANCE':'LBS_EXTRA_SOBRE_ORDEN'})
        overshoot['LBS_EXTRA_SOBRE_ORDEN'] = overshoot['LBS_EXTRA_SOBRE_ORDEN'].abs()
        lnk_key = lnk_col if lnk_col else 'LNK'
        overshoot_cols = [c for c in ['MIX', lnk_key, 'LBS_EXTRA_SOBRE_ORDEN','LBS_ASIGNADAS'] if c in overshoot.columns]
        overshoot = overshoot[overshoot_cols]
    else:
        overshoot = pd.DataFrame(columns=['MIX','LNK','LBS_EXTRA_SOBRE_ORDEN','LBS_ASIGNADAS'])

    # ── RESUMEN_CATEGORIA ────────────────────────────────────────────────────
    res_cat = (result.groupby('CATEGORIA')
               .agg(Lotes         =('LOTE_ID','nunique'),
                    Registros      =('LOTE_ID','count'),
                    LBS_Loteadas   =('TOTAL_LOTE', lambda x: result.loc[x.index].groupby('LOTE_ID')['TOTAL_LOTE'].first().sum()),
                    Puros          =('TIPO_LOTE_ANCHO', lambda x: (x=='PURO').sum()),
                    Mix_Controlado =('TIPO_LOTE_ANCHO', lambda x: (x=='MIX_CONTROLADO').sum()),
                    Mix_Alto       =('TIPO_LOTE_ANCHO', lambda x: (x=='MIX_ALTO').sum()),
                    Avg_Fill_Pct   =('PCT_CARGA_REAL',  'mean'))
               .reset_index())
    res_cat['Avg_Fill_Pct'] = res_cat['Avg_Fill_Pct'].round(1)

    # ── PARAMETROS — configuración usada ─────────────────────────────────────
    param_rows = []
    for c in capacidades:
        for k, v in c.items():
            param_rows.append({'CATEGORIA': c['CATEGORIA'], 'PARAMETRO': k, 'VALOR': v})
    parametros = pd.DataFrame(param_rows)

    return {
        'DETALLE_LOTES':          detalle,
        'RESUMEN_LOTES':          resumen,
        'RESUMEN_CATEGORIA':      res_cat,
        'EXCEDENTES':             excedentes,
        'CAPACIDAD_X_CATEG':      cap_df,
        'PRIORIDAD_VS_ASIG':      prio_df,
        'LNK_COMPLETITUD':        lnk_comp,
        'REPORTE_REGLAS_MIX':     reglas_mix,
        'OVERSHOOT_SUMMARY':      overshoot,
        'PARAMETROS':             parametros,
    }


def run_all(df, capacidades, config):
    max_items      = to_int(config.get('MAX_ITEMS', 8))
    solver_timeout = to_float(config.get('SOLVER_TIMEOUT', 5))
    active_caps    = [c for c in capacidades if c.get('ACTIVO', True)]

    all_rows         = []
    usados_global    = set()   # índices ya loteados — evita que un ítem entre en 2 categorías

    for idx, cap in enumerate(active_caps):
        cat = cap['CATEGORIA']

        # Pasar df sin los índices ya usados en categorías anteriores
        df_disponible = df[~df.index.isin(usados_global)].copy()
        lotes, grupo = run_loteador(df_disponible, cap, max_items, solver_timeout)

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
                usados_global.add(i)   # marcar como usado globalmente

    if not all_rows:
        return pd.DataFrame(), {}

    result = pd.DataFrame(all_rows)
    show   = ['CATEGORIA','LOTE_ID','COLOR_A','ESTILO_C','ANCHO','LBS_C',
              'TOTAL_LOTE','PCT_CARGA_REAL','SET_ANCHOS_LOTE','CANT_ANCHOS',
              'TIPO_LOTE_ANCHO','MIX','TIPO_TEJIDO','PCT_CARGA','PRIORIDAD','COLOR_R','FAMILIA',
              'LNK','LNK_PRIORIDAD','TONO','CONSUMO_C','STYLE']
    show   = [c for c in show if c in result.columns]
    result = result[show].sort_values(['CATEGORIA','LOTE_ID']).reset_index(drop=True)

    reports = _build_reports(result, df, capacidades)
    return result, reports

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

        with col_d:
            st.write("")   # spacer

        # Descarga del perfil — fuera de columnas, key dinamico por nombre
        profiles_fresh = load_profiles()   # recargar para reflejar guardados recientes
        if sel != "(ninguno)" and sel in profiles_fresh:
            profile_json = json.dumps(profiles_fresh[sel], indent=2, default=str).encode()
            st.download_button(
                label=f"⬇ Descargar '{sel}'",
                data=profile_json,
                file_name=f"perfil_{sel.replace(' ','_')}.json",
                mime="application/json",
                use_container_width=True,
                key=f"dl_profile_btn_{hash(sel) % 99999}",
            )
        else:
            st.caption("Selecciona un perfil para descargar")

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

    updated    = []
    total_cap  = 0

    for i, cap in enumerate(caps):
        activo = bool(cap.get('ACTIVO', True))
        c = st.columns([0.35, 1.1, 0.75, 0.75, 0.65, 0.65, 0.95, 0.65, 0.65, 0.75, 0.85, 0.85])

        activo_new  = c[0].checkbox("", value=activo, key=f"ca_{i}")
        cat         = c[1].text_input("", value=str(cap.get('CATEGORIA','')),  key=f"cc_{i}", label_visibility="collapsed")
        minv        = c[2].number_input("", value=to_int(cap.get('MINIMO',1000)),  key=f"cmin_{i}", step=100, min_value=0, label_visibility="collapsed")
        maxv        = c[3].number_input("", value=to_int(cap.get('MAXIMO',1100)),  key=f"cmax_{i}", step=100, min_value=1, label_visibility="collapsed")
        lotes       = c[4].number_input("", value=to_int(cap.get('LOTES',5)),      key=f"cl_{i}",  step=1,   min_value=1, label_visibility="collapsed")
        # Semanas: guardado como float, paso 0.1 para mayor precisión
        sem_raw     = cap.get('SEMANAS', 4.0)
        sem_val     = round(float(sem_raw) if sem_raw is not None else 4.0, 2)
        semanas     = c[5].number_input("", value=sem_val, key=f"cs_{i}", step=0.1, min_value=0.1, format="%.1f", label_visibility="collapsed")
        cap_calc    = int(round(lotes * DIAS_SEMANA * float(semanas) * maxv))
        c[6].markdown(f"<div style='padding-top:6px'><span class='badge badge-blue'>{cap_calc:,} lbs</span></div>", unsafe_allow_html=True)
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
        if activo_new:
            total_cap += cap_calc

    # ── FILA TOTAL ────────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style='display:flex;gap:8px;margin-top:8px;padding:8px 12px;
        background:#003876;border-radius:6px;align-items:center;'>
        <span style='color:#cce4ff;font-size:10px;font-weight:700;flex:2'>TOTAL ACTIVAS</span>
        <span style='color:white;font-size:12px;font-weight:800;flex:1'>{total_cap:,} lbs</span>
        </div>""",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Agregar Categoría"):
        updated.append({"CATEGORIA":"NUEVA","MINIMO":1000,"MAXIMO":1100,"LOTES":5,"SEMANAS":4.0,
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

        result_holder = [None, {}]
        error_holder  = [None]

        caps_actuales = st.session_state.get('capacidades', DEFAULT_CAPACIDADES)
        st.session_state['caps_usadas'] = caps_actuales

        def _run():
            try:
                res, reps = run_all(
                    df,
                    caps_actuales,
                    st.session_state.get('config', DEFAULT_CONFIG),
                )
                result_holder[0] = res
                result_holder[1] = reps
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
            st.session_state['reportes']  = result_holder[1]
            n_lotes = result['LOTE_ID'].nunique()
            elapsed = round(time.time() - start, 1)
            st.success(f"✅ Completado en {elapsed}s: **{n_lotes} lotes** generados con **{len(result)} registros**. Ve a **Resultados**.")

# ─── TAB 5: RESULTADOS ──────────────────────────────────────────────────────────
def tab_resultados():
    st.markdown("### Resultados del Loteador")

    result   = st.session_state.get('resultado', None)
    reportes = st.session_state.get('reportes', {})

    if result is None:
        st.info("Aún no hay resultados. Ve a **▶ Ejecutar** para correr el loteador.")
        return

    # ── MÉTRICAS ─────────────────────────────────────────────────────────────
    n_lotes   = result['LOTE_ID'].nunique()
    total_lbs = result.groupby('LOTE_ID')['TOTAL_LOTE'].first().sum()
    cats_n    = result['CATEGORIA'].nunique()
    puro_n    = result[result['TIPO_LOTE_ANCHO']=='PURO']['LOTE_ID'].nunique()
    puro_pct  = round(puro_n / n_lotes * 100, 1) if n_lotes else 0
    sin_asig  = reportes.get('EXCEDENTES', pd.DataFrame())
    sin_asig_n = len(sin_asig) if not sin_asig.empty else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.markdown(f"<div class='metric-box'><div class='metric-val'>{n_lotes}</div><div class='metric-lbl'>Lotes Generados</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-box'><div class='metric-val'>{total_lbs:,.0f}</div><div class='metric-lbl'>Total LBS Loteadas</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-box'><div class='metric-val'>{cats_n}</div><div class='metric-lbl'>Categorías Usadas</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-box'><div class='metric-val'>{puro_pct}%</div><div class='metric-lbl'>% Lotes Puros</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='metric-box'><div class='metric-val' style='color:#c0392b'>{sin_asig_n}</div><div class='metric-lbl'>Sin Asignar</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── TABS DE REPORTES ─────────────────────────────────────────────────────
    rt1, rt2, rt3, rt4, rt5, rt6, rt7, rt8 = st.tabs([
        "📋 Detalle Lotes",
        "📊 Resumen Lotes",
        "🏭 Capacidad x Categ",
        "⚖ Prioridad vs Asig",
        "⚠ Excedentes",
        "🔗 LNK Completitud",
        "📐 Reglas MIX",
        "📁 Resumen Categoría",
    ])

    with rt1:
        st.caption("Detalle de cada ítem asignado a un lote")
        df_det = reportes.get('DETALLE_LOTES', result)
        cf1, cf2, cf3 = st.columns(3)
        with cf1:
            cat_f = st.selectbox("Categoría", ["Todas"] + sorted(result['CATEGORIA'].unique().tolist()), key="r_cat")
        with cf2:
            tipo_f = st.selectbox("Tipo Lote", ["Todos"] + sorted(result['TIPO_LOTE_ANCHO'].dropna().unique().tolist()), key="r_tipo")
        with cf3:
            mix_f = st.selectbox("MIX", ["Todos"] + sorted(result['MIX'].dropna().unique().tolist()), key="r_mix")
        df_show = df_det.copy()
        if 'CATEGORIA' in df_show.columns:
            if cat_f  != "Todas": df_show = df_show[df_show['CATEGORIA'] == cat_f]
        if 'MIX' in df_show.columns:
            if mix_f  != "Todos": df_show = df_show[df_show['MIX'] == mix_f]
        st.dataframe(df_show, use_container_width=True, height=420)

    with rt2:
        st.caption("Un registro por lote con totales y métricas de calidad")
        df_res = reportes.get('RESUMEN_LOTES', pd.DataFrame())
        st.dataframe(df_res, use_container_width=True, height=420)

    with rt3:
        st.caption("LBS asignadas vs capacidad planeada por categoría")
        df_cap = reportes.get('CAPACIDAD_X_CATEG', pd.DataFrame())
        if not df_cap.empty:
            # Color rows: verde si diferencia>0, rojo si <0
            st.dataframe(df_cap, use_container_width=True, height=300)
            # mini bar chart
            chart_data = df_cap.set_index('CATEGORIA')[['CAPACIDAD_LBS','LBS_ASIGNADAS']] if 'CAPACIDAD_LBS' in df_cap.columns else None
            if chart_data is not None:
                st.bar_chart(chart_data)
        else:
            st.info("Sin datos")

    with rt4:
        st.caption("LBS base vs asignadas agrupadas por MIX y PRIORIDAD")
        df_prio = reportes.get('PRIORIDAD_VS_ASIG', pd.DataFrame())
        st.dataframe(df_prio, use_container_width=True, height=300)

    with rt5:
        st.caption("Ítems que no pudieron ser asignados a ningún lote")
        df_exc = reportes.get('EXCEDENTES', pd.DataFrame())
        if df_exc.empty:
            st.success("✅ Todos los ítems fueron asignados a un lote.")
        else:
            st.warning(f"⚠ {len(df_exc)} ítems sin asignar")
            st.dataframe(df_exc, use_container_width=True, height=350)

    with rt6:
        st.caption("Estado de completitud por LNK/SKU — qué tan completo quedó cada corte")
        df_lnk = reportes.get('LNK_COMPLETITUD', pd.DataFrame())
        if not df_lnk.empty and 'ESTADO' in df_lnk.columns:
            completos  = (df_lnk['ESTADO']=='COMPLETO').sum()
            parciales  = (df_lnk['ESTADO']=='PARCIAL').sum()
            excedidos  = (df_lnk['ESTADO']=='EXCEDIDO').sum()
            sin_asig   = (df_lnk['ESTADO']=='SIN_ASIGNAR').sum()
            lc1,lc2,lc3,lc4 = st.columns(4)
            lc1.markdown(f"<div class='metric-box'><div class='metric-val' style='color:#1a7a4a'>{completos}</div><div class='metric-lbl'>Completos</div></div>", unsafe_allow_html=True)
            lc2.markdown(f"<div class='metric-box'><div class='metric-val' style='color:#e67e22'>{parciales}</div><div class='metric-lbl'>Parciales</div></div>", unsafe_allow_html=True)
            lc3.markdown(f"<div class='metric-box'><div class='metric-val' style='color:#c0392b'>{excedidos}</div><div class='metric-lbl'>Excedidos</div></div>", unsafe_allow_html=True)
            lc4.markdown(f"<div class='metric-box'><div class='metric-val' style='color:#7f8c8d'>{sin_asig}</div><div class='metric-lbl'>Sin Asignar</div></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            # Filter
            est_opts = ['Todos'] + sorted(df_lnk['ESTADO'].unique().tolist())
            est_f = st.selectbox("Filtrar estado", est_opts, key="lnk_est")
            df_lnk_show = df_lnk if est_f == 'Todos' else df_lnk[df_lnk['ESTADO']==est_f]
            st.dataframe(df_lnk_show, use_container_width=True, height=380)
        elif not df_lnk.empty:
            st.dataframe(df_lnk, use_container_width=True, height=380)
        else:
            st.info("No hay columna LNK/SKU disponible en los datos. Agrega una columna 'LNK' a tu hoja DATA.")

    with rt7:
        st.caption("Resumen de reglas aplicadas por lote y tipo de ancho")
        df_reg = reportes.get('REPORTE_REGLAS_MIX', pd.DataFrame())
        st.dataframe(df_reg, use_container_width=True, height=350)

    with rt8:
        st.caption("Resumen agregado por categoría: lotes, LBS, tipos de mezcla")
        df_rcat = reportes.get('RESUMEN_CATEGORIA', pd.DataFrame())
        st.dataframe(df_rcat, use_container_width=True, height=300)

    # ── DESCARGA ─────────────────────────────────────────────────────────────
    st.markdown("---")
    tz    = pytz.timezone("America/Tegucigalpa")
    ts    = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    fname = f"loteo_OPTIMO_{ts}.xlsx"
    buf   = BytesIO()
    sheet_order = [
        ('DETALLE_LOTES',      reportes.get('DETALLE_LOTES',      result)),
        ('RESUMEN_LOTES',      reportes.get('RESUMEN_LOTES',      pd.DataFrame())),
        ('RESUMEN_CATEGORIA',  reportes.get('RESUMEN_CATEGORIA',  pd.DataFrame())),
        ('EXCEDENTES',         reportes.get('EXCEDENTES',         pd.DataFrame())),
        ('CAPACIDAD_X_CATEG',  reportes.get('CAPACIDAD_X_CATEG',  pd.DataFrame())),
        ('PRIORIDAD_VS_ASIG',  reportes.get('PRIORIDAD_VS_ASIG',  pd.DataFrame())),
        ('LNK_COMPLETITUD',    reportes.get('LNK_COMPLETITUD',    pd.DataFrame())),
        ('REPORTE_REGLAS_MIX', reportes.get('REPORTE_REGLAS_MIX', pd.DataFrame())),
        ('OVERSHOOT_SUMMARY',  reportes.get('OVERSHOOT_SUMMARY',  pd.DataFrame())),
        ('PARAMETROS',         reportes.get('PARAMETROS',         pd.DataFrame())),
    ]
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        for sheet_name, df_sheet in sheet_order:
            if df_sheet is not None and not df_sheet.empty:
                df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
        _format_excel_output(writer)
    buf.seek(0)
    st.download_button("⬇ Descargar Excel completo", data=buf, file_name=fname,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=False)

# ─── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    sidebar()

    st.markdown("""
    <div class="logo-header">
      <div style="font-size:18px;font-weight:800;color:white;letter-spacing:0.5px;">🏭 Loteador Óptimo de Tintorería</div>
      <div style="font-size:9px;color:#cce4ff;letter-spacing:2px;text-transform:uppercase;margin-top:3px;">Grupo Elcatex · Planeacion de la Demanda · Honduras 🇭🇳</div>
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
