"""
Planeacion de la Demanda — Grupo Elcatex
Solo requiere la hoja DATA del Excel.
"""

import streamlit as st
import pandas as pd
import numpy as np
import re, io, base64
from pathlib import Path

# ============================================================
# COLORES ELCATEX
# ============================================================
BLUE_DARK  = "#1A2E6B"   # azul marino del círculo externo
BLUE_MID   = "#1565C0"   # azul medio (ELCATEX letras)
BLUE_LIGHT = "#2196F3"   # azul claro acento
GRAY_LOGO  = "#9E9E9E"   # gris "GRUPO"
WHITE      = "#FFFFFF"
LIGHT_BG   = "#F0F4FF"   # fondo suave azulado

# ============================================================
# PAGE CONFIG + CSS
# ============================================================
st.set_page_config(
    page_title="Planeación de la Demanda — Elcatex",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
  /* ---- Fondo general ---- */
  .stApp {{ background-color: {LIGHT_BG}; }}

  /* ---- Sidebar fondo ---- */
  [data-testid="stSidebar"] {{
      background: linear-gradient(180deg, {BLUE_DARK} 0%, {BLUE_MID} 100%);
  }}

  /* Etiquetas, headings y texto libre en sidebar → blanco */
  [data-testid="stSidebar"] label {{ color: {WHITE} !important; }}
  [data-testid="stSidebar"] p     {{ color: {WHITE} !important; }}
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3   {{ color: {WHITE} !important; }}
  [data-testid="stSidebar"] .stMarkdown {{ color: {WHITE} !important; }}
  [data-testid="stSidebar"] [data-testid="stSliderTickBarMin"],
  [data-testid="stSidebar"] [data-testid="stSliderTickBarMax"] {{ color: rgba(255,255,255,0.7) !important; }}
  [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.25); }}

  /* Inputs numéricos/texto → fondo blanco con texto oscuro (legible) */
  [data-testid="stSidebar"] input[type="number"],
  [data-testid="stSidebar"] input[type="text"] {{
      background-color: {WHITE} !important;
      color: {BLUE_DARK} !important;
      -webkit-text-fill-color: {BLUE_DARK} !important;
      border-radius: 6px !important;
  }}

  /* File uploader → borde punteado blanco, texto blanco, botón semitransparente */
  [data-testid="stSidebar"] [data-testid="stFileUploader"] {{
      background-color: rgba(255,255,255,0.12) !important;
      border: 2px dashed rgba(255,255,255,0.55) !important;
      border-radius: 10px !important;
      padding: 8px !important;
  }}
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
      color: {WHITE} !important;
      -webkit-text-fill-color: {WHITE} !important;
  }}
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
      background-color: rgba(255,255,255,0.22) !important;
      border: 1px solid rgba(255,255,255,0.5) !important;
      color: {WHITE} !important;
      -webkit-text-fill-color: {WHITE} !important;
  }}
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] svg {{
      fill: {WHITE} !important;
  }}

  /* ---- Header banner ---- */
  .elcatex-header {{
      background: linear-gradient(90deg, {BLUE_DARK} 0%, {BLUE_MID} 60%, {BLUE_LIGHT} 100%);
      padding: 18px 28px;
      border-radius: 12px;
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      gap: 20px;
  }}
  .elcatex-header h1 {{
      color: {WHITE};
      font-size: 1.6rem;
      margin: 0;
      font-weight: 700;
      letter-spacing: 1px;
  }}
  .elcatex-header p {{
      color: rgba(255,255,255,0.80);
      margin: 2px 0 0 0;
      font-size: 0.85rem;
  }}

  /* ---- Metric cards ---- */
  [data-testid="stMetric"] {{
      background: {WHITE};
      border: 1px solid #C5D3F0;
      border-radius: 10px;
      padding: 14px 18px;
      box-shadow: 0 2px 6px rgba(21,101,192,0.10);
  }}
  [data-testid="stMetricLabel"] {{ color: {BLUE_MID} !important; font-weight: 600; }}
  [data-testid="stMetricValue"] {{ color: {BLUE_DARK} !important; }}

  /* ---- Tabs ---- */
  .stTabs [data-baseweb="tab-list"] {{
      background: {WHITE};
      border-radius: 10px 10px 0 0;
      border-bottom: 2px solid {BLUE_MID};
      gap: 4px;
  }}
  .stTabs [data-baseweb="tab"] {{
      color: {BLUE_MID};
      font-weight: 600;
      border-radius: 8px 8px 0 0;
      padding: 8px 18px;
  }}
  .stTabs [aria-selected="true"] {{
      background: {BLUE_MID} !important;
      color: {WHITE} !important;
  }}

  /* ---- Primary button ---- */
  .stButton > button[kind="primary"] {{
      background: linear-gradient(90deg, {BLUE_DARK}, {BLUE_MID});
      color: {WHITE};
      border: none;
      border-radius: 8px;
      font-weight: 700;
      letter-spacing: 0.5px;
      padding: 10px 0;
  }}
  .stButton > button[kind="primary"]:hover {{
      background: linear-gradient(90deg, {BLUE_MID}, {BLUE_LIGHT});
      transform: translateY(-1px);
  }}

  /* ---- Dataframe ---- */
  [data-testid="stDataFrame"] {{ border-radius: 8px; overflow: hidden; }}

  /* ---- Section headers in main ---- */
  .section-title {{
      color: {BLUE_DARK};
      font-weight: 700;
      font-size: 1.05rem;
      border-left: 4px solid {BLUE_MID};
      padding-left: 10px;
      margin: 16px 0 10px 0;
  }}

  /* ---- Config table rows ---- */
  .cfg-row {{
      background: {WHITE};
      border: 1px solid #C5D3F0;
      border-radius: 8px;
      padding: 10px 14px;
      margin-bottom: 8px;
  }}
</style>
""", unsafe_allow_html=True)

# ---- Logo en base64 desde upload ----
LOGO_PATH = Path("/mnt/user-data/uploads/1781641564899_image.png")
def get_logo_b64():
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return None

logo_b64 = get_logo_b64()
logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:56px;border-radius:50%;">' \
    if logo_b64 else "🧵"

st.markdown(f"""
<div class="elcatex-header">
  {logo_html}
  <div>
    <h1>Planeación de la Demanda</h1>
    <p>Grupo Elcatex · Planificación 2026 · Lideramos, Cuidamos, Hacemos la Diferencia.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# UTILS
# ============================================================
def norm_str(x):
    if pd.isna(x): return ""
    return str(x).strip()
def up(x): return norm_str(x).upper()
def clean_cols(cols):
    out = []
    for c in cols:
        c = "" if c is None else str(c)
        c = c.replace("\n"," ").replace("\r"," ")
        c = re.sub(r"\s+"," ",c).strip()
        out.append(c)
    return out
def parse_float_list(s):
    parts = re.split(r"[;,\s]+", str(s).strip())
    vals = []
    for p in parts:
        try: vals.append(float(p))
        except: pass
    return vals

# ============================================================
# DEFAULTS DE CAPACIDADES
# ============================================================
CAP_DEFAULTS = [
    # (etiqueta_label, mix,      minimo, maximo, capacidad, activa)
    ("A-4000", "DYE",    3301, 4000, 999_999, True),
    ("B-3300", "DYE",    2601, 3300, 999_999, True),
    ("C-2600", "DYE",    2201, 2600, 999_999, True),
    ("D-2200", "DYE",    1101, 2200, 999_999, True),
    ("E-1100", "DYE",     100, 1100, 999_999, True),
    ("A-4000", "BLEACH", 3301, 4000, 999_999, True),
    ("B-3300", "BLEACH", 2601, 3300, 999_999, True),
    ("C-2600", "BLEACH", 2201, 2600, 999_999, True),
    ("D-2200", "BLEACH", 1101, 2200, 999_999, True),
    ("E-1100", "BLEACH",  100, 1100, 999_999, True),
]

# Max anchos por categoría (label → max_widths_for_category)
CAP_MAX_WIDTHS_DEFAULT = {
    "A-4000": 6,
    "B-3300": 6,
    "C-2600": 4,
    "D-2200": 4,
    "E-1100": 2,
}

# COMBINACIONES de prioridad permitidas
COMB_DEFAULTS = [
    ("VENCIDOS", "VENCIDOS", True),
    ("VENCIDOS", "AHEAD",    False),
    ("AHEAD",    "AHEAD",    True),
    ("AHEAD",    "AHEAD2",   False),
    ("AHEAD2",   "AHEAD2",   True),
    ("OTROS",    "OTROS",    True),
]

# ============================================================
# BLOCKS & WIDTHS
# ============================================================
def prioridad_bloque(prio_text: str) -> str:
    p = (prio_text or "").upper()
    if "PAST DUE" in p or "DUE" in p or "VENC" in p: return "VENCIDOS"
    if "AHEAD2" in p: return "AHEAD2"
    if "AHEAD" in p:  return "AHEAD"
    return "OTROS"

def can_mix_blocks(b1, b2, allowed_pairs):
    return b1 == b2 or (b1, b2) in allowed_pairs

def valid_width_group(widths, min_diff, max_diff, max_widths):
    w = [float(x) for x in widths if x is not None and not pd.isna(x) and float(x)!=0.0]
    uw = sorted(set(w))
    if len(uw)<=1: return True
    if len(uw)>int(max_widths): return False
    for i in range(len(uw)):
        for j in range(i+1,len(uw)):
            d = abs(uw[j]-uw[i])
            if d<min_diff or d>max_diff: return False
    return True

def get_row_widths(work, idx):
    widths=[]
    for c in ["ANCHO.F.C","ANCHO.F.M"]:
        if c in work.columns:
            v = work.at[idx,c]
            if pd.notna(v) and float(v)!=0.0:
                widths.append(float(v))
    return widths

# ============================================================
# SPLIT CHOOSER
# ============================================================
def choose_take(rest, remaining, split_min_lbs, allow_scrap_residue=False):
    try: split_min_lbs=float(split_min_lbs)
    except: split_min_lbs=0.0
    if rest<=0 or remaining<=0: return 0.0
    if rest<=remaining+1e-9:    return float(rest)
    take=float(remaining)
    if take+1e-9<split_min_lbs: return 0.0
    residue=float(rest)-take
    if residue>1e-9 and residue+1e-9<split_min_lbs:
        if not allow_scrap_residue: return 0.0
        return take
    return take

# ============================================================
# RANGES BUILDER
# ============================================================
def build_ranges(df_cap):
    ranges=[]
    for _,r in df_cap.iterrows():
        ranges.append({
            "CATEGORIA": norm_str(r["CATEGORIA"]),
            "LABEL":     norm_str(r.get("LABEL", r["CATEGORIA"])),
            "MINIMO":    float(r["MINIMO"]),
            "MAXIMO":    float(r["MAXIMO"]),
            "CAPACIDAD": float(r["CAPACIDAD"]),
            "MIX":       up(r["MIX"]),
            "MAX_WIDTHS_CAT": int(r.get("MAX_WIDTHS_CAT", 6)),
            "RANGO_ID":  f"CAP_{norm_str(r['CATEGORIA'])}_{up(r['MIX'])}_{float(r['MAXIMO']):.0f}"
        })
    # Mayor a menor (llenar categorías grandes primero)
    return sorted(ranges, key=lambda x: x["MAXIMO"], reverse=True)

# ============================================================
# LOAD DATA — solo hoja DATA
# ============================================================
def load_data(xlsm_bytes):
    xls = pd.ExcelFile(xlsm_bytes, engine="openpyxl")
    if "DATA" not in xls.sheet_names:
        raise ValueError(f"No se encontró la hoja DATA. Hojas presentes: {xls.sheet_names}")
    req_cols=["LNK","TELA.CUERPO","COLOR","PRIORIDAD","ANCHO.F.C","ANCHO.F.M","TOTAL","MIX","CONSUMO_C"]
    preview=pd.read_excel(xlsm_bytes,sheet_name="DATA",engine="openpyxl",header=None,nrows=80)
    req_set=set(req_cols); hdr_row=0
    for r in range(80):
        row_vals={norm_str(v) for v in preview.iloc[r].tolist() if norm_str(v)}
        if req_set.issubset(row_vals): hdr_row=r; break
    df=pd.read_excel(xlsm_bytes,sheet_name="DATA",engine="openpyxl",header=hdr_row)
    df.columns=clean_cols(df.columns)
    miss=[c for c in req_cols if c not in df.columns]
    if miss: raise ValueError(f"DATA: faltan columnas {miss}. Header fila {hdr_row+1}.")
    for c in ["ANCHO.F.C","ANCHO.F.M","TOTAL","CONSUMO_C"]:
        df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0.0)
    for c in ["LNK","TELA.CUERPO","COLOR","PRIORIDAD","MIX"]:
        df[c]=df[c].apply(norm_str)
    df["MIX"]=df["MIX"].apply(up)
    for col in ["FAMILIA","COLOR_R","STYLE"]:
        df[col]=df[col].apply(up) if col in df.columns else ""
    if "TONO" in df.columns: df["TONO"]=df["TONO"].apply(up)
    df=df[df["LNK"].str.len()>0].copy()
    df=df[df["TOTAL"]>0].copy()
    df=df.reset_index(drop=True)
    return df, hdr_row

# ============================================================
# BUILD PARAMS
# ============================================================
def build_params(ui):
    allowed_pairs=set()
    for b1,b2,activa in ui["combinaciones"]:
        if activa:
            allowed_pairs.add((b1,b2)); allowed_pairs.add((b2,b1))
    return {
        "MIN_DIFF":             ui["min_diff"],
        "MAX_DIFF":             ui["max_diff"],
        "MAX_WIDTHS":           ui["max_widths_global"],
        "MAX_SKU":              ui["max_sku"],
        "MIX_ALLOWED":          allowed_pairs,
        "RESTRICCIONES_FAMILIA":{},
        "RESTRICCIONES_COLOR":  {},
        "RESTRICCIONES_ANCHO":  {},
        "REGLAS_ANCHOS_COMBINADOS":[],
        "RULE_ORDER":           "ANCHO18>COMBO_ANCHOS>COLOR_R>FAMILIA>DEFAULT",
        "PRIORITY_ORDER":       "",
        "APPLY_RULES_BLEACH":   0,
        "OVERRIDE_BY_PRIORITY": 1,
        "TRY_ALL_PRIORITIES":   1,
        "UPGRADE_CATEGORIA":    1,
        "SPLIT_MIN_LBS_DEFAULT":ui["split_min"],
        "SPLIT_MIN_LBS_ANCHO18":ui["split_min"],
        "SCRAP_REMAINDER_BELOW_SPLIT_MIN": 1,
        "ANCHO18_ALLOW_SPILLOVER_2600": 0,
        "ANCHO18_ALLOWED_MAX_DYE": {2200.0,1100.0},
        "BEAM_WIDTH":           ui["beam_width"],
        "W_FILL":               5.0,
        "W_CAP_LOSS":           3.0,
        "WIDTH_PREF_LIST":      [2,3,1,4,5,6],
        "W_WIDTH_PREF":         2.0,
        "W_1100_WIDTHS_STRICT": 10.0,
        "WIDTHS_TARGET_ORDER":  "2>3>4",
        "REQUIRE_WIDTHS_STRICT":1,
        "ALLOWED_MAXIMO_FOR_3_WIDTHS":{"DYE":set(),"BLEACH":set()},
        "ALLOWED_MAXIMO_FOR_4_WIDTHS":{"DYE":set(),"BLEACH":set()},
        # Priorizar VENCIDOS solos primero
        "VENCIDOS_FIRST": True,
    }

# ============================================================
# PRIORITY HELPERS
# ============================================================
def order_priorities(pris, params):
    pris=[float(x) for x in pris if x is not None]
    return sorted(pris)

def order_by_priorities(base_ranges, prioridades):
    used=set(); out=[]
    for cap in prioridades:
        for r in base_ranges:
            if abs(float(r["MAXIMO"])-float(cap))<1e-6 and id(r) not in used:
                out.append(r); used.add(id(r))
    for r in base_ranges:
        if id(r) not in used: out.append(r)
    return out

# ============================================================
# REORDER RULES
# ============================================================
def reorder_ranges_for_seed(ranges_mix, mixv, work, seed_idx, params):
    base=list(ranges_mix)
    rule_info={"regla_aplicada":"NONE","prioridades":[],"match_combo":False,
               "limite_ancho_style":None,"origen_prioridad":"MIX","combo_target_width":None}
    if up(mixv) not in ("DYE",) and int(params.get("APPLY_RULES_BLEACH",0))!=1:
        return base, rule_info

    fam     =up(work.at[seed_idx,"FAMILIA"]) if "FAMILIA" in work.columns else ""
    color_r =up(work.at[seed_idx,"COLOR_R"]) if "COLOR_R" in work.columns else ""
    style   =up(work.at[seed_idx,"STYLE"])   if "STYLE"   in work.columns else ""
    def f2(x):
        try: return float(x)
        except: return 0.0
    ancho_c=f2(work.at[seed_idx,"ANCHO.F.C"]) if "ANCHO.F.C" in work.columns else 0.0
    ancho_m=f2(work.at[seed_idx,"ANCHO.F.M"]) if "ANCHO.F.M" in work.columns else 0.0
    restr_fam   =params.get("RESTRICCIONES_FAMILIA",{})
    restr_color =params.get("RESTRICCIONES_COLOR",{})
    restr_ancho =params.get("RESTRICCIONES_ANCHO",{})
    reglas_combo=params.get("REGLAS_ANCHOS_COMBINADOS",[])
    rule_order  =[x.strip().upper() for x in
                  norm_str(params.get("RULE_ORDER","")).split(">") if x.strip()] or \
                 ["ANCHO18","COMBO_ANCHOS","COLOR_R","FAMILIA","DEFAULT"]

    def ancho_leq(ac,am,lim):
        vals=[]
        try:
            if ac and not pd.isna(ac) and float(ac)>0: vals.append(float(ac))
        except: pass
        try:
            if am and not pd.isna(am) and float(am)>0: vals.append(float(am))
        except: pass
        return len(vals)>0 and min(vals)<=float(lim)

    def try_ancho18():
        if style in restr_ancho:
            lim=restr_ancho[style].get("limite",None)
            pris=order_priorities(restr_ancho[style].get("prioridades",[]),params)
            if lim is not None and ancho_leq(ancho_c,ancho_m,lim) and pris:
                rule_info.update({"regla_aplicada":"ANCHO18","prioridades":list(pris),
                                   "limite_ancho_style":lim,"origen_prioridad":"STYLE"})
                return order_by_priorities(base,pris)
    def try_combo():
        for regla in reglas_combo:
            a1,a2=regla["a1"],regla["a2"]
            pris=order_priorities(regla["prioridades"],params)
            sm=any(abs(v-a)<1e-6 for v in [ancho_c,ancho_m] for a in [a1,a2])
            if not sm: continue
            obj=a2 if(abs(ancho_c-a1)<1e-6 or abs(ancho_m-a1)<1e-6) else a1
            existe=any(abs(f2(work.at[i,"ANCHO.F.C"])-obj)<1e-6 or
                       abs(f2(work.at[i,"ANCHO.F.M"])-obj)<1e-6
                       for i in work.index
                       if i!=seed_idx and float(work.at[i,"LBS_RESTANTES"])>0)
            if existe and pris:
                rule_info.update({"regla_aplicada":"COMBO_ANCHOS","prioridades":list(pris),
                                   "match_combo":True,"origen_prioridad":"COMBO","combo_target_width":float(obj)})
                return order_by_priorities(base,pris)
    def try_color_r():
        if color_r in restr_color and restr_color[color_r]:
            p=float(restr_color[color_r])
            rule_info.update({"regla_aplicada":"COLOR_R","prioridades":[p],"origen_prioridad":"COLOR"})
            return order_by_priorities(base,[p])
    def try_familia():
        if fam in restr_fam and restr_fam[fam]:
            pris=order_priorities(restr_fam[fam],params)
            rule_info.update({"regla_aplicada":"FAMILIA","prioridades":list(pris),"origen_prioridad":"FAMILIA"})
            return order_by_priorities(base,pris)
    dispatch={"ANCHO18":try_ancho18,"COMBO_ANCHOS":try_combo,
              "COLOR_R":try_color_r,"FAMILIA":try_familia,"DEFAULT":lambda:base}
    for token in rule_order:
        fn=dispatch.get(token)
        if fn:
            out=fn()
            if out is not None: return out, rule_info
    return base, rule_info

# ============================================================
# SCORING
# ============================================================
def score_lote(lote_dict, resumen_rows, params):
    if lote_dict is None: return -1e30
    W_FILL     =params.get("W_FILL",5.0)
    W_CAP_LOSS =params.get("W_CAP_LOSS",3.0)
    W_WP       =params.get("W_WIDTH_PREF",2.0)
    W_1100     =params.get("W_1100_WIDTHS_STRICT",10.0)
    pref_list  =params.get("WIDTH_PREF_LIST",[2,3,1,4,5,6])
    total =float(lote_dict.get("TOTAL_LOTE",0.0))
    maximo=float(lote_dict.get("MAXIMO",1.0))
    fill  =total/maximo if maximo>1e-9 else 0.0
    cap_loss=maximo-total
    anchos={float(w) for r in resumen_rows for w in r.get("ANCHOS_ROW",[]) if w is not None}
    wu=len(anchos)
    try:    rank=pref_list.index(wu)
    except: rank=len(pref_list)+abs(wu-pref_list[-1])
    score=W_FILL*fill - W_CAP_LOSS*cap_loss + W_WP*(-float(rank))
    if abs(maximo-1100.0)<1e-6: score-=W_1100*max(0,wu-1)
    return score

# ============================================================
# INTENTAR LOTE — usa max_widths por categoría
# ============================================================
def intentar_lote_para_rango(work, seed_idx, rango, capacity_used, params, rule_info,
                              require_two_widths=False, split_min_lbs=None,
                              min_unique_widths=None, max_unique_widths=None):
    min_diff    =params["MIN_DIFF"]; max_diff=params["MAX_DIFF"]
    max_widths  =params["MAX_WIDTHS"]; max_sku=params["MAX_SKU"]
    allowed_pairs=params["MIX_ALLOWED"]
    rid         =rango["RANGO_ID"]
    cap_left    =max(0.0,float(rango["CAPACIDAD"])-float(capacity_used.get(rid,0.0)))
    if cap_left<=0: return None
    max_allowed =min(float(rango["MAXIMO"]),cap_left)
    if float(work.at[seed_idx,"LBS_RESTANTES"])<=0: return None

    # Max anchos para esta categoría específica
    cat_max_widths=int(rango.get("MAX_WIDTHS_CAT", max_widths))
    effective_max_widths=min(max_widths, cat_max_widths)
    if max_unique_widths is not None:
        effective_max_widths=min(effective_max_widths, int(max_unique_widths))

    try: split_min_lbs=float(split_min_lbs or params.get("SPLIT_MIN_LBS_DEFAULT",500.0))
    except: split_min_lbs=float(params.get("SPLIT_MIN_LBS_DEFAULT",500.0))
    allow_scrap=int(params.get("SCRAP_REMAINDER_BELOW_SPLIT_MIN",1))==1

    lote_rows=[]; lote_lbs=0.0; lote_lnks=set(); lote_blocks=[]; lote_widths=[]

    def can_add_row(idx, lbs_to_add):
        if lbs_to_add<=0: return False
        if "TONO" in work.columns:
            st_=up(work.at[seed_idx,"TONO"]) if not pd.isna(work.at[seed_idx,"TONO"]) else ""
            rt_=up(work.at[idx,"TONO"])      if not pd.isna(work.at[idx,"TONO"])      else ""
            if st_!=rt_: return False
        if len(set(lote_lnks)|{work.at[idx,"LNK"]})>max_sku: return False
        b=work.at[idx,"BLOQUE"]
        if any(not can_mix_blocks(eb,b,allowed_pairs) for eb in lote_blocks): return False
        wc=list(lote_widths)+get_row_widths(work,idx)
        if not valid_width_group(wc, min_diff, max_diff, effective_max_widths): return False
        return lote_lbs+lbs_to_add<=max_allowed+1e-9

    seed_rest=float(work.at[seed_idx,"LBS_RESTANTES"])
    remaining=max_allowed-lote_lbs
    take=choose_take(seed_rest,remaining,split_min_lbs,allow_scrap_residue=allow_scrap)
    if take<=0 or not can_add_row(seed_idx,take): return None

    lote_rows.append((seed_idx,take,0.0,0.0))
    lote_lbs+=take; lote_lnks.add(work.at[seed_idx,"LNK"])
    lote_blocks.append(work.at[seed_idx,"BLOQUE"])
    lote_widths+=get_row_widths(work,seed_idx)
    combo_target=rule_info.get("combo_target_width") if rule_info else None
    pref_list=params.get("WIDTH_PREF_LIST",[2,3,1,4,5,6])

    while True:
        remaining=max_allowed-lote_lbs
        if remaining<=1e-6: break
        best=None; best_take=0.0; best_score=-1e30
        widths_now={float(w) for w in lote_widths if w and not pd.isna(w) and float(w)!=0.0}
        n_now=len(widths_now)
        width_target=int(min_unique_widths) if min_unique_widths is not None else None

        for idx in work.index:
            rest=float(work.at[idx,"LBS_RESTANTES"])
            if rest<=0 or any(i==idx for i,*_ in lote_rows): continue
            take=choose_take(rest,remaining,split_min_lbs,allow_scrap_residue=allow_scrap)
            if take<=0 or not can_add_row(idx,take): continue
            widths_add={float(w) for w in get_row_widths(work,idx)
                        if w and not pd.isna(w) and float(w)!=0.0}
            n_after=len(widths_now|widths_add)
            fill_score=lote_lbs+take
            width_prog=(max(0,(width_target or 0)-n_now)-max(0,(width_target or 0)-n_after))*500.0
            combo_hit=1000.0 if combo_target and any(
                abs(float(w)-float(combo_target))<1e-6 for w in widths_add) else 0.0
            try:    pref_sc=-float(pref_list.index(n_after))*50.0
            except: pref_sc=-(len(pref_list)+abs(n_after-pref_list[-1]))*50.0
            over_pen=-2000.0*max(0,n_after-(width_target or 999))
            sc=fill_score+width_prog+combo_hit+pref_sc+over_pen
            if sc>best_score: best_score=sc; best=idx; best_take=take

        if best is None: break
        lote_rows.append((best,best_take,0.0,0.0)); lote_lbs+=best_take
        lote_lnks.add(work.at[best,"LNK"]); lote_blocks.append(work.at[best,"BLOQUE"])
        lote_widths+=get_row_widths(work,best)

    if lote_lbs+1e-9<float(rango["MINIMO"]): return None
    uw=sorted({float(w) for w in lote_widths if w and not pd.isna(w) and float(w)!=0.0})
    min_req=int(min_unique_widths) if min_unique_widths is not None else (2 if require_two_widths else None)
    if min_req is not None and len(uw)<min_req: return None
    if len(uw)>effective_max_widths: return None

    return {"RANGO_ID":rango["RANGO_ID"],"CATEGORIA":rango["CATEGORIA"],
            "LABEL":rango.get("LABEL",rango["CATEGORIA"]),
            "MIX":rango["MIX"],"MINIMO":float(rango["MINIMO"]),"MAXIMO":float(rango["MAXIMO"]),
            "TOTAL_LOTE":float(lote_lbs),"ROWS":lote_rows,"REQUIERE_2_ANCHOS":bool(require_two_widths)}

# ============================================================
# RUN LOTEO — VENCIDOS PRIMERO, luego combinaciones
# ============================================================
def run_loteo(df_data, df_cap, params, progress_callback=None):
    ranges=build_ranges(df_cap)   # ya ordenado mayor a menor MAXIMO
    capacity_used={r["RANGO_ID"]:0.0 for r in ranges}
    data=df_data.copy()
    data["BLOQUE"]=data["PRIORIDAD"].apply(prioridad_bloque)
    data["LBS_RESTANTES"]=data["TOTAL"].astype(float)
    data["LBS_SCRAP"]=0.0
    detalle=[]; resumen=[]; lote_id_global=1
    vencidos_first=params.get("VENCIDOS_FIRST",True)

    # Orden de bloques: primero VENCIDOS solos, luego con combinaciones
    block_order_pass1=["VENCIDOS"]                      # solo vencidos
    block_order_pass2=["VENCIDOS","AHEAD","AHEAD2","OTROS"]  # con mezclas

    group_keys=["TELA.CUERPO","MIX"]
    group_keys.insert(1,"TONO" if "TONO" in data.columns else "COLOR")
    groups=list(data.groupby(group_keys).groups.items())

    for gi,(keys,grp_idx) in enumerate(groups):
        if progress_callback:
            progress_callback(gi/len(groups),f"Grupo {gi+1}/{len(groups)}…")
        work=data.loc[grp_idx].copy()
        tela,tono_or_color,mixv=keys[0],keys[1],keys[2]
        ranges_mix=[r for r in ranges if r["MIX"]==mixv]
        if not ranges_mix: continue

        def run_pass(block_order_list, allow_mix):
            nonlocal lote_id_global
            blocked=set()
            while True:
                work["LBS_RESTANTES"]=pd.to_numeric(work["LBS_RESTANTES"],errors="coerce").fillna(0.0)
                if (work["LBS_RESTANTES"]>0).sum()==0: break
                made_any=False
                for b in block_order_list:
                    if b in blocked: continue
                    cand=work[(work["BLOQUE"]==b)&(work["LBS_RESTANTES"]>0)]
                    if len(cand)==0: blocked.add(b); continue
                    beam_w=int(params.get("BEAM_WIDTH",3))
                    top_seeds=cand.sort_values("LBS_RESTANTES",ascending=False).head(beam_w).index.tolist()
                    best_lote=None; best_pack=None; best_score=-1e30

                    for seed_idx in top_seeds:
                        ranges_try,rule_info=reorder_ranges_for_seed(ranges_mix,mixv,work,seed_idx,params)
                        if rule_info.get("regla_aplicada")=="ANCHO18" and up(mixv)=="DYE":
                            allowed=set(params.get("ANCHO18_ALLOWED_MAX_DYE",{2200.0,1100.0}))
                            if params.get("ANCHO18_ALLOW_SPILLOVER_2600",0)==1: allowed.add(2600.0)
                            ranges_try=[r for r in ranges_try if float(r["MAXIMO"]) in allowed]

                        # Si no se permiten mezclas (pass 1), filtrar seeds del bloque actual
                        if not allow_mix:
                            allowed_pairs_now={(b,b)}
                            rule_info_now=dict(rule_info)
                            # override: solo mismo bloque
                            params_now=dict(params)
                            params_now["MIX_ALLOWED"]=allowed_pairs_now
                        else:
                            params_now=params

                        lote=None; prioridad_obj=None
                        split_min=float(params.get("SPLIT_MIN_LBS_DEFAULT",500.0))

                        for r in ranges_try:
                            if capacity_used[r["RANGO_ID"]]>=r["CAPACIDAD"]-1e-6: continue
                            intento=intentar_lote_para_rango(
                                work,seed_idx,r,capacity_used,params_now,rule_info,
                                require_two_widths=False,split_min_lbs=split_min)
                            if intento:
                                lote=intento; break

                        if lote:
                            rs=[{"LNK":work.at[i,"LNK"],"ANCHOS_ROW":get_row_widths(work,i)}
                                for i,*_ in lote["ROWS"]]
                            sc=score_lote({"MAXIMO":float(lote["MAXIMO"]),"TOTAL_LOTE":float(lote["TOTAL_LOTE"])},rs,params)
                            if sc>best_score:
                                best_score=sc; best_lote=lote
                                best_pack=(lote,rule_info,prioridad_obj,best_score)

                    if best_lote is None: blocked.add(b); continue

                    lote,rule_info,prioridad_obj,best_score=best_pack
                    split_min=float(params.get("SPLIT_MIN_LBS_DEFAULT",500.0))
                    lote_id=f"L{lote_id_global:06d}"; lote_id_global+=1
                    all_w=[]
                    for i,*_ in lote["ROWS"]: all_w+=get_row_widths(work,i)
                    anchos_lote=sorted({float(w) for w in all_w if w and not pd.isna(w) and float(w)!=0.0})
                    anchos_str=str(anchos_lote)
                    regla_final=rule_info.get("regla_aplicada","NONE")

                    for idx,lbs_asig,oe,us in lote["ROWS"]:
                        detalle.append({
                            "LOTE_ID":lote_id,"ANCHOS_LOTE":anchos_str,
                            "CATEGORIA":lote["CATEGORIA"],"LABEL":lote.get("LABEL",lote["CATEGORIA"]),
                            "MIX":lote["MIX"],"TELA.CUERPO":tela,
                            "COLOR":work.at[idx,"COLOR"],
                            "TONO":work.at[idx,"TONO"] if "TONO" in work.columns else "",
                            "LNK":work.at[idx,"LNK"],"PRIORIDAD":work.at[idx,"PRIORIDAD"],
                            "BLOQUE":work.at[idx,"BLOQUE"],
                            "ANCHO.F.C":float(work.at[idx,"ANCHO.F.C"]),
                            "ANCHO.F.M":float(work.at[idx,"ANCHO.F.M"]),
                            "CONSUMO_C":float(work.at[idx,"CONSUMO_C"]),
                            "FAMILIA":work.at[idx,"FAMILIA"],
                            "COLOR_R":work.at[idx,"COLOR_R"],
                            "STYLE":work.at[idx,"STYLE"],
                            "LBS_ASIGNADAS":float(lbs_asig),
                            "APLICA_REGLA":regla_final,
                            "PRIORIDAD_USADA":float(lote["MAXIMO"]),
                            "DECISION_SCORE":float(best_score),
                        })
                        work.at[idx,"LBS_RESTANTES"]=max(0.0,float(work.at[idx,"LBS_RESTANTES"])-float(lbs_asig))
                        rem=float(work.at[idx,"LBS_RESTANTES"])
                        if rem>1e-9 and rem+1e-9<float(split_min):
                            work.at[idx,"LBS_SCRAP"]+=rem
                            work.at[idx,"LBS_RESTANTES"]=0.0

                    bloques=[d["BLOQUE"] for d in detalle if d["LOTE_ID"]==lote_id]
                    resumen.append({
                        "LOTE_ID":lote_id,"LABEL":lote.get("LABEL",lote["CATEGORIA"]),
                        "ANCHOS_LOTE":anchos_str,"CATEGORIA":lote["CATEGORIA"],"MIX":lote["MIX"],
                        "TELA.CUERPO":tela,"COLOR_TONO":tono_or_color,
                        "LBS_TOTAL":float(lote["TOTAL_LOTE"]),
                        "MIN_RANGO":float(lote["MINIMO"]),"MAX_RANGO":float(lote["MAXIMO"]),
                        "CAPACIDAD_PERDIDA":float(lote["MAXIMO"]-lote["TOTAL_LOTE"]),
                        "SKU_DISTINTOS":len({d["LNK"] for d in detalle if d["LOTE_ID"]==lote_id}),
                        "ANCHOS_UNICOS":len(anchos_lote),
                        "BLOQUE_DOMINANTE":max(set(bloques),key=bloques.count) if bloques else "",
                        "REGLA_DOMINANTE":regla_final,"PRIORIDAD_FINAL":float(lote["MAXIMO"]),
                    })
                    capacity_used[lote["RANGO_ID"]]+=float(lote["TOTAL_LOTE"])
                    blocked=set(); made_any=True; break
                if not made_any: break

        # PASS 1: solo VENCIDOS sin mezcla
        if vencidos_first:
            run_pass(block_order_pass1, allow_mix=False)
        # PASS 2: todos los bloques con mezclas permitidas
        run_pass(block_order_pass2, allow_mix=True)

        data.loc[work.index,"LBS_RESTANTES"]=work["LBS_RESTANTES"]
        data.loc[work.index,"LBS_SCRAP"]=work["LBS_SCRAP"]

    if progress_callback: progress_callback(1.0,"¡Listo!")
    exced_cols=["LNK","TELA.CUERPO","COLOR","MIX","PRIORIDAD","BLOQUE",
                "ANCHO.F.C","ANCHO.F.M","TOTAL","LBS_RESTANTES","LBS_SCRAP"]
    if "TONO" in data.columns: exced_cols.insert(3,"TONO")
    exced=data[data["LBS_RESTANTES"]>1e-9][exced_cols].copy()
    df_det=pd.DataFrame(detalle)
    if len(df_det)>0:
        df_det["DOCENAS"]=np.where(df_det["CONSUMO_C"]>0,df_det["LBS_ASIGNADAS"]/df_det["CONSUMO_C"],np.nan)
    df_res=pd.DataFrame(resumen)
    return df_det,df_res,exced

# ============================================================
# REPORTS
# ============================================================
def build_reports(df_data, df_cap, df_det, df_res):
    df_cap_s=df_cap[["CATEGORIA","LABEL","MIX","MINIMO","MAXIMO","CAPACIDAD","MAX_WIDTHS_CAT"]].copy()
    agg=df_det.groupby(["CATEGORIA","MIX"],as_index=False)["LBS_ASIGNADAS"].sum() \
        if len(df_det)>0 else pd.DataFrame({"CATEGORIA":[],"MIX":[],"LBS_ASIGNADAS":[]})
    df_cc=df_cap_s.merge(agg,on=["CATEGORIA","MIX"],how="left").fillna({"LBS_ASIGNADAS":0.0})
    df_cc["DIFERENCIA"]=df_cc["LBS_ASIGNADAS"]-df_cc["CAPACIDAD"]
    df_cc=df_cc.sort_values(["MIX","MAXIMO"],ascending=[True,False])

    df_data2=df_data.copy()
    df_data2["BLOQUE"]=df_data2["PRIORIDAD"].apply(prioridad_bloque)
    pb=df_data2.groupby(["MIX","BLOQUE"],as_index=False)["TOTAL"].sum().rename(columns={"TOTAL":"LBS_BASE"})
    pa=df_det.groupby(["MIX","BLOQUE"],as_index=False)["LBS_ASIGNADAS"].sum() \
        if len(df_det)>0 else pd.DataFrame({"MIX":[],"BLOQUE":[],"LBS_ASIGNADAS":[]})
    pv=pb.merge(pa,on=["MIX","BLOQUE"],how="left").fillna({"LBS_ASIGNADAS":0.0})
    pv["LBS_SIN_ASIGNAR"]=pv["LBS_BASE"]-pv["LBS_ASIGNADAS"]
    ob=["VENCIDOS","AHEAD","AHEAD2","OTROS"]
    pv["_o"]=pv["BLOQUE"].apply(lambda x:ob.index(x) if x in ob else 99)
    pv=pv.sort_values(["MIX","_o"]).drop(columns=["_o"])

    lb=df_data.groupby(["MIX","LNK"],as_index=False)["TOTAL"].sum().rename(columns={"TOTAL":"LBS_BASE"})
    ls=df_data.groupby(["MIX","LNK"],as_index=False)["LBS_SCRAP"].sum() \
        if "LBS_SCRAP" in df_data.columns else pd.DataFrame({"MIX":[],"LNK":[],"LBS_SCRAP":[]})
    la=df_det.groupby(["MIX","LNK"],as_index=False)["LBS_ASIGNADAS"].sum() \
        if len(df_det)>0 else pd.DataFrame({"MIX":[],"LNK":[],"LBS_ASIGNADAS":[]})
    lc=(lb.merge(la,on=["MIX","LNK"],how="left")
          .merge(ls,on=["MIX","LNK"],how="left")
          .fillna({"LBS_ASIGNADAS":0.0,"LBS_SCRAP":0.0}))
    lc["BALANCE"]=lc["LBS_BASE"]-lc["LBS_ASIGNADAS"]-lc["LBS_SCRAP"]
    lc["ESTADO"]=np.where(lc["BALANCE"].abs()<=1e-6,
                           np.where(lc["LBS_SCRAP"]>1e-6,"COMPLETO (SCRAP)","COMPLETO"),"INCOMPLETO")
    lc=lc.sort_values(["MIX","ESTADO","BALANCE"],ascending=[True,True,False])
    return {"CAPACIDAD_X_CATEG":df_cc,"PRIORIDAD_VS_ASIG":pv,"LNK_COMPLETITUD":lc}

# ============================================================
# EXPORTAR EXCEL
# ============================================================
def exportar_excel(df_det,df_res,df_exced,reports):
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as w:
        df_det.to_excel(w,index=False,sheet_name="DETALLE_LOTES")
        df_res.to_excel(w,index=False,sheet_name="RESUMEN_LOTES")
        df_exced.to_excel(w,index=False,sheet_name="EXCEDENTES")
        reports["CAPACIDAD_X_CATEG"].to_excel(w,index=False,sheet_name="CAPACIDAD_X_CATEG")
        reports["PRIORIDAD_VS_ASIG"].to_excel(w,index=False,sheet_name="PRIORIDAD_VS_ASIG")
        reports["LNK_COMPLETITUD"].to_excel(w,index=False,sheet_name="LNK_COMPLETITUD")
    buf.seek(0); return buf.read()

# ============================================================
# =====================  STREAMLIT UI  =======================
# ============================================================

# ---------- SIDEBAR ----------
with st.sidebar:
    # Logo pequeño
    if logo_b64:
        st.markdown(f'<div style="text-align:center;margin-bottom:10px;">'
                    f'<img src="data:image/png;base64,{logo_b64}" style="height:70px;border-radius:50%;"></div>',
                    unsafe_allow_html=True)
    st.markdown(f'<p style="text-align:center;font-size:0.75rem;color:rgba(255,255,255,0.7);">'
                f'Loteo Tintorería NV2</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📂 Archivo")
    uploaded=st.file_uploader("Sube tu .xlsx (hoja DATA)", type=["xlsx","xlsm"])
    st.markdown("---")

    # ==== PARAMS ====
    st.markdown("### ⚙️ Parámetros")
    max_diff   =st.number_input("Diff. máx. entre anchos (pulgadas)", value=6.0, step=0.5,
                                   help="Diferencia máxima permitida entre anchos en un mismo lote")
    min_diff = 0.0  # siempre 0: sin límite mínimo de diferencia
    max_sku    =st.number_input("Max SKUs por lote",       value=6,   step=1, min_value=1)
    split_min  =st.number_input("Split mínimo LBS",        value=500.0,step=50.0)
    beam_width =st.slider("Beam Width",1,10,3)
    venc_first =st.checkbox("Priorizar VENCIDOS solos primero",value=True)

# ---------- MAIN AREA: CONFIG TABLES ----------
st.markdown('<p class="section-title">📋 Configuración — edita directamente en las tablas</p>',
            unsafe_allow_html=True)

# ==== CAPACIDADES como data_editor ====
st.markdown("#### 🏭 Capacidades Tintorería")
st.caption("Marca **Activa** para incluir la categoría en el loteo. Edita capacidad y max anchos directamente en la tabla.")

if "cap_df" not in st.session_state:
    st.session_state["cap_df"] = pd.DataFrame([
        {
            "Activa":       act,
            "Categoría":    l,
            "MIX":          m,
            "Mín (lbs)":    mn,
            "Máx (lbs)":    mx,
            "Capacidad":    int(cap),
            "Max Anchos":   CAP_MAX_WIDTHS_DEFAULT.get(l, 6),
        }
        for l,m,mn,mx,cap,act in CAP_DEFAULTS
    ])

cap_edited = st.data_editor(
    st.session_state["cap_df"],
    use_container_width=True,
    height=420,
    hide_index=True,
    column_config={
        "Activa":      st.column_config.CheckboxColumn("✅ Activa",
                           help="Marca para incluir esta categoría en el loteo"),
        "Categoría":   st.column_config.TextColumn("Categoría", disabled=True),
        "MIX":         st.column_config.TextColumn("MIX", disabled=True),
        "Mín (lbs)":   st.column_config.NumberColumn("Mín (lbs)", disabled=True, format="%d"),
        "Máx (lbs)":   st.column_config.NumberColumn("Máx (lbs)", disabled=True, format="%d"),
        "Capacidad":   st.column_config.NumberColumn(
                           "Capacidad (lbs)",
                           help="Cuántas lbs en total puede recibir esta categoría en el plan",
                           min_value=0, step=1000, format="%d"),
        "Max Anchos":  st.column_config.NumberColumn(
                           "Max Anchos por Lote",
                           help="Número máximo de anchos distintos permitidos en un mismo lote de esta categoría",
                           min_value=1, max_value=10, step=1),
    },
    key="cap_editor",
)
st.session_state["cap_df"] = cap_edited

st.markdown("---")

# ==== COMBINACIONES como data_editor ====
st.markdown("#### 🔀 Combinaciones de Prioridad")
st.caption("Marca **Permitida** para que esos dos bloques de prioridad puedan ir en el mismo lote.")

if "comb_df" not in st.session_state:
    st.session_state["comb_df"] = pd.DataFrame([
        {
            "Permitida":    act,
            "Bloque 1":     b1,
            "Bloque 2":     b2,
            "Descripción":  f"Solo {b1}" if b1==b2 else f"{b1} y {b2} pueden mezclarse en un lote",
        }
        for b1,b2,act in COMB_DEFAULTS
    ])

comb_edited = st.data_editor(
    st.session_state["comb_df"],
    use_container_width=True,
    height=265,
    hide_index=True,
    column_config={
        "Permitida":    st.column_config.CheckboxColumn("✅ Permitida"),
        "Bloque 1":     st.column_config.TextColumn("Bloque 1",   disabled=True),
        "Bloque 2":     st.column_config.TextColumn("Bloque 2",   disabled=True),
        "Descripción":  st.column_config.TextColumn("Descripción",disabled=True),
    },
    key="comb_editor",
)
st.session_state["comb_df"] = comb_edited

st.markdown("---")

# ---------- EJECUTAR ----------
if uploaded is None:
    st.info("👈 Sube tu archivo Excel con la hoja DATA para comenzar.")
    st.stop()

file_bytes=uploaded.read()

if st.button("🚀 Ejecutar Loteo", type="primary", use_container_width=True):
    progress_bar=st.progress(0,text="Iniciando…")
    try:
        def upd(pct,msg): progress_bar.progress(min(pct,1.0),text=msg)

        with st.spinner("Cargando DATA…"):
            df_data,hdr_row=load_data(io.BytesIO(file_bytes))
        st.success(f"✅ {len(df_data):,} filas cargadas (header fila {hdr_row+1})")

        # Construir df_cap desde data_editor
        cap_df = st.session_state["cap_df"]
        active_df = cap_df[cap_df["Activa"]==True]
        if len(active_df)==0:
            st.error("❌ Debes tener al menos una categoría activa."); st.stop()

        df_cap=pd.DataFrame([{
            "CATEGORIA":     str(row["Categoría"]),
            "LABEL":         str(row["Categoría"]),
            "MIX":           str(row["MIX"]).upper(),
            "MINIMO":        float(row["Mín (lbs)"]),
            "MAXIMO":        float(row["Máx (lbs)"]),
            "CAPACIDAD":     float(row["Capacidad"]),
            "MAX_WIDTHS_CAT":int(row["Max Anchos"]),
        } for _,row in active_df.iterrows()])

        # Construir combinaciones desde data_editor
        comb_df = st.session_state["comb_df"]
        combinaciones = [
            (str(row["Bloque 1"]), str(row["Bloque 2"]), bool(row["Permitida"]))
            for _,row in comb_df.iterrows()
        ]

        ui_params={
            "min_diff":          min_diff,
            "max_diff":          max_diff,
            "max_widths_global": int(active_df["Max Anchos"].max()),
            "max_sku":           int(max_sku),
            "split_min":         split_min,
            "beam_width":        beam_width,
            "combinaciones":     combinaciones,
        }
        params=build_params(ui_params)
        params["VENCIDOS_FIRST"]=venc_first

        df_det,df_res,df_exced=run_loteo(df_data,df_cap,params,progress_callback=upd)
        progress_bar.progress(1.0,text="Construyendo reportes…")
        reports=build_reports(df_data,df_cap,df_det,df_res)
        xlsx_bytes=exportar_excel(df_det,df_res,df_exced,reports)

        st.session_state["res"]={
            "df_det":df_det,"df_res":df_res,"df_exced":df_exced,
            "reports":reports,"xlsx_bytes":xlsx_bytes,
        }
        progress_bar.empty()
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ {e}"); st.exception(e)

# ---------- RESULTADOS ----------
if "res" in st.session_state:
    r=st.session_state["res"]
    df_det=r["df_det"]; df_res=r["df_res"]; df_exced=r["df_exced"]; reports=r["reports"]

    st.markdown('<p class="section-title">📊 Resultados</p>', unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("🗂️ Lotes generados",  f"{len(df_res):,}")
    c2.metric("⚖️ LBS asignadas",    f"{df_det['LBS_ASIGNADAS'].sum():,.0f}" if len(df_det)>0 else "0")
    c3.metric("⚠️ Excedentes",       f"{len(df_exced):,}")
    c4.metric("📉 Capacidad perdida", f"{df_res['CAPACIDAD_PERDIDA'].sum():,.0f} lbs" if len(df_res)>0 else "0")

    st.download_button("📥 Descargar RESULTADOS_LOTES.xlsx",data=r["xlsx_bytes"],
                       file_name="RESULTADOS_LOTES.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True,type="primary")

    tab1,tab2,tab3,tab4,tab5=st.tabs([
        "📋 Resumen Lotes","🔍 Detalle","⚠️ Excedentes","📊 Capacidad x Categ.","✅ LNK Completitud"])

    with tab1:
        st.dataframe(df_res,use_container_width=True,height=450)
    with tab2:
        mx_opts=["Todos"]+sorted(df_det["MIX"].unique().tolist()) if len(df_det)>0 else ["Todos"]
        mx_sel=st.selectbox("Filtrar MIX",mx_opts)
        show=df_det if mx_sel=="Todos" else df_det[df_det["MIX"]==mx_sel]
        st.dataframe(show,use_container_width=True,height=450)
    with tab3:
        if len(df_exced)>0:
            st.warning(f"{len(df_exced)} filas sin asignar.")
            st.dataframe(df_exced,use_container_width=True)
        else:
            st.success("🎉 Sin excedentes.")
    with tab4:
        st.dataframe(reports["CAPACIDAD_X_CATEG"].style.background_gradient(
            subset=["LBS_ASIGNADAS"],cmap="Blues"),use_container_width=True)
    with tab5:
        cmap_={"COMPLETO":"background-color:#d4edda","COMPLETO (SCRAP)":"background-color:#fff3cd",
               "INCOMPLETO":"background-color:#f8d7da"}
        def hl(row): return [cmap_.get(row["ESTADO"],"")] * len(row)
        st.dataframe(reports["LNK_COMPLETITUD"].style.apply(hl,axis=1),use_container_width=True)
