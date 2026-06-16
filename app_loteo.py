"""
NV2 Loteo Tintorería - Streamlit App
Solo requiere la hoja DATA del Excel.
Todos los parámetros, capacidades y reglas viven en el código / sidebar.
"""

import streamlit as st
import pandas as pd
import numpy as np
import re
import io

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="NV2 Loteo Tintorería",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🧵 NV2 Loteo Tintorería 2026")
st.markdown("Sube tu archivo `.xlsx` con la hoja **DATA** y ajusta los parámetros en el panel izquierdo.")

# ============================================================
# UTILS
# ============================================================
def norm_str(x):
    if pd.isna(x): return ""
    return str(x).strip()

def up(x):
    return norm_str(x).upper()

def clean_cols(cols):
    out = []
    for c in cols:
        c = "" if c is None else str(c)
        c = c.replace("\n", " ").replace("\r", " ")
        c = re.sub(r"\s+", " ", c).strip()
        out.append(c)
    return out

# ============================================================
# CAPACIDADES HARDCODEADAS
# Fuente: hoja CAPACIDADES_TINTO del template original.
# Editar aquí si cambian los rangos de la tintorería.
# ============================================================
CAPACIDADES_DEFAULT = [
    # (CATEGORIA, MIX,     MINIMO,  MAXIMO,   CAPACIDAD)
    ("CHICO",     "DYE",     100,    1100,    999_999),
    ("MEDIANO",   "DYE",    1101,    2200,    999_999),
    ("GRANDE",    "DYE",    2201,    2600,    999_999),
    ("CHICO",     "BLEACH",  100,    1100,    999_999),
    ("MEDIANO",   "BLEACH", 1101,    2200,    999_999),
    ("GRANDE",    "BLEACH", 2201,    2600,    999_999),
]

def make_df_cap(capacidades=None):
    rows = capacidades or CAPACIDADES_DEFAULT
    df = pd.DataFrame(rows, columns=["CATEGORIA", "MIX", "MINIMO", "MAXIMO", "CAPACIDAD"])
    df["MIX"] = df["MIX"].apply(up)
    return df

# ============================================================
# REGLAS HARDCODEADAS
# Fuente: hojas de restricciones del template original.
# Editar aquí para agregar/quitar restricciones sin tocar el Excel.
# ============================================================

# COMBINACIONES_PRIORIDAD: qué bloques de prioridad pueden mezclarse en un mismo lote
COMBINACIONES_PRIORIDAD = [
    ("VENCIDOS", "AHEAD"),
    ("AHEAD",    "AHEAD2"),
]

# RESTRICCIONES_FAMILIA: dict { FAMILIA -> [lista de MAXIMO permitidos en orden de prioridad] }
RESTRICCIONES_FAMILIA = {
    "PC78/90": [2200.0, 1100.0],
}

# RESTRICCIONES_COLOR: dict { COLOR_R -> MAXIMO preferido }
RESTRICCIONES_COLOR = {
    # "OSCURO": 2200.0,
}

# RESTRICCIONES_ANCHO (ANCHO18): dict { STYLE -> {"limite": float, "prioridades": [list]} }
RESTRICCIONES_ANCHO = {
    # "MI_STYLE": {"limite": 18.0, "prioridades": [1100.0, 2200.0]},
}

# REGLAS_ANCHOS_COMBINADOS: list of { a1, a2, prioridades }
REGLAS_ANCHOS_COMBINADOS = [
    # {"a1": 18.0, "a2": 26.0, "prioridades": [2200.0]},
]

def build_rules():
    allowed_pairs = set()
    for a, b in COMBINACIONES_PRIORIDAD:
        allowed_pairs.add((a, b)); allowed_pairs.add((b, a))
    return allowed_pairs

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
    w = [float(x) for x in widths if x is not None and not pd.isna(x) and float(x) != 0.0]
    uw = sorted(set(w))
    if len(uw) <= 1: return True
    if len(uw) > int(max_widths): return False
    for i in range(len(uw)):
        for j in range(i + 1, len(uw)):
            d = abs(uw[j] - uw[i])
            if d < min_diff or d > max_diff: return False
    return True

def get_row_widths(work, idx):
    widths = []
    for c in ["ANCHO.F.C", "ANCHO.F.M"]:
        if c in work.columns:
            v = work.at[idx, c]
            if pd.notna(v) and float(v) != 0.0:
                widths.append(float(v))
    return widths

# ============================================================
# SPLIT CHOOSER — estricto, sin tolerancias
# ============================================================
def choose_take(rest, remaining, split_min_lbs, allow_scrap_residue=False):
    try:    split_min_lbs = float(split_min_lbs)
    except: split_min_lbs = 0.0
    if rest <= 0 or remaining <= 0: return 0.0
    if rest <= remaining + 1e-9:    return float(rest)
    take = float(remaining)
    if take + 1e-9 < split_min_lbs: return 0.0
    residue = float(rest) - take
    if residue > 1e-9 and residue + 1e-9 < split_min_lbs:
        if not allow_scrap_residue: return 0.0
        return take
    return take

# ============================================================
# RANGES BUILDER
# ============================================================
def build_ranges(df_cap):
    ranges = []
    for _, r in df_cap.iterrows():
        ranges.append({
            "CATEGORIA": norm_str(r["CATEGORIA"]),
            "MINIMO":    float(r["MINIMO"]),
            "MAXIMO":    float(r["MAXIMO"]),
            "CAPACIDAD": float(r["CAPACIDAD"]),
            "MIX":       up(r["MIX"]),
            "RANGO_ID":  f"CAP_{norm_str(r['CATEGORIA'])}_{up(r['MIX'])}_{float(r['MAXIMO']):.0f}"
        })
    return sorted(ranges, key=lambda x: x["MAXIMO"], reverse=True)

# ============================================================
# LOAD DATA — solo hoja DATA
# ============================================================
def load_data(xlsm_bytes):
    xls = pd.ExcelFile(xlsm_bytes, engine="openpyxl")
    if "DATA" not in xls.sheet_names:
        raise ValueError(f"No se encontró la hoja DATA. Hojas presentes: {xls.sheet_names}")

    req_cols = ["LNK", "TELA.CUERPO", "COLOR", "PRIORIDAD",
                "ANCHO.F.C", "ANCHO.F.M", "TOTAL", "MIX", "CONSUMO_C"]

    # Auto-detectar fila de encabezado
    preview = pd.read_excel(xlsm_bytes, sheet_name="DATA", engine="openpyxl",
                            header=None, nrows=80)
    req_set = set(req_cols)
    hdr_row = 0
    for r in range(80):
        row_vals = set(norm_str(v) for v in preview.iloc[r].tolist() if norm_str(v))
        if req_set.issubset(row_vals):
            hdr_row = r
            break

    df = pd.read_excel(xlsm_bytes, sheet_name="DATA", engine="openpyxl", header=hdr_row)
    df.columns = clean_cols(df.columns)

    miss = [c for c in req_cols if c not in df.columns]
    if miss:
        raise ValueError(f"DATA: faltan columnas {miss}. Header detectado en fila {hdr_row+1}.")

    for c in ["ANCHO.F.C", "ANCHO.F.M", "TOTAL", "CONSUMO_C"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    for c in ["LNK", "TELA.CUERPO", "COLOR", "PRIORIDAD", "MIX"]:
        df[c] = df[c].apply(norm_str)
    df["MIX"] = df["MIX"].apply(up)

    for col in ["FAMILIA", "COLOR_R", "STYLE"]:
        df[col] = df[col].apply(up) if col in df.columns else ""
    if "TONO" in df.columns:
        df["TONO"] = df["TONO"].apply(up)

    # Filtrar filas sin datos útiles
    df = df[df["LNK"].str.len() > 0].copy()
    df = df[df["TOTAL"] > 0].copy()
    df = df.reset_index(drop=True)

    return df, hdr_row

# ============================================================
# BUILD PARAMS — desde sidebar + reglas hardcodeadas
# ============================================================
def build_params(ui):
    allowed_pairs = build_rules()
    return {
        "MIN_DIFF":                    ui["min_diff"],
        "MAX_DIFF":                    ui["max_diff"],
        "MAX_WIDTHS":                  ui["max_widths"],
        "MAX_SKU":                     ui["max_sku"],
        "MIX_ALLOWED":                 allowed_pairs,
        "RESTRICCIONES_FAMILIA":       RESTRICCIONES_FAMILIA,
        "RESTRICCIONES_COLOR":         RESTRICCIONES_COLOR,
        "RESTRICCIONES_ANCHO":         RESTRICCIONES_ANCHO,
        "REGLAS_ANCHOS_COMBINADOS":    REGLAS_ANCHOS_COMBINADOS,
        "RULE_ORDER":                  "ANCHO18>COMBO_ANCHOS>COLOR_R>FAMILIA>DEFAULT",
        "PRIORITY_ORDER":              "",
        "APPLY_RULES_BLEACH":          0,
        "OVERRIDE_BY_PRIORITY":        1,
        "TRY_ALL_PRIORITIES":          1,
        "UPGRADE_CATEGORIA":           1,
        "SPLIT_MIN_LBS_DEFAULT":       ui["split_min_default"],
        "SPLIT_MIN_LBS_ANCHO18":       ui["split_min_ancho18"],
        "SCRAP_REMAINDER_BELOW_SPLIT_MIN": 1,
        "ANCHO18_ALLOW_SPILLOVER_2600":0,
        "ANCHO18_ALLOWED_MAX_DYE":     {2200.0, 1100.0},
        "BEAM_WIDTH":                  ui["beam_width"],
        "W_FILL":                      5.0,
        "W_CAP_LOSS":                  3.0,
        "WIDTH_PREF_LIST":             [2, 3, 1, 4, 5, 6],
        "W_WIDTH_PREF":                2.0,
        "W_1100_WIDTHS_STRICT":        10.0,
        "WIDTHS_TARGET_ORDER":         ui["widths_target_order"],
        "REQUIRE_WIDTHS_STRICT":       1 if ui["require_strict"] else 0,
        "ALLOWED_MAXIMO_FOR_3_WIDTHS": {"DYE": set(ui["allowed_3w_dye"]),   "BLEACH": set()},
        "ALLOWED_MAXIMO_FOR_4_WIDTHS": {"DYE": set(ui["allowed_4w_dye"]),   "BLEACH": set()},
    }

# ============================================================
# PRIORITY HELPERS
# ============================================================
def order_priorities(pris, params):
    pris = [float(x) for x in pris if x is not None]
    po_text = norm_str(params.get("PRIORITY_ORDER", ""))
    if po_text:
        plan = [p.strip() for p in po_text.split(">") if p.strip()]
        rank = {float(v): i for i, v in enumerate(plan) if re.match(r"^\d+(\.\d+)?$", v)}
        return sorted(pris, key=lambda x: (rank.get(float(x), 10_000), float(x)))
    return sorted(pris)

def order_by_priorities(base_ranges, prioridades):
    used = set(); out = []
    for cap in prioridades:
        for r in base_ranges:
            if abs(float(r["MAXIMO"]) - float(cap)) < 1e-6 and id(r) not in used:
                out.append(r); used.add(id(r))
    for r in base_ranges:
        if id(r) not in used: out.append(r)
    return out

# ============================================================
# REORDER RULES
# ============================================================
def reorder_ranges_for_seed(ranges_mix, mixv, work, seed_idx, params):
    base = list(ranges_mix)
    rule_info = {"regla_aplicada": "NONE", "prioridades": [], "match_combo": False,
                 "limite_ancho_style": None, "origen_prioridad": "MIX", "combo_target_width": None}
    if up(mixv) not in ("DYE",) and int(params.get("APPLY_RULES_BLEACH", 0)) != 1:
        return base, rule_info

    fam     = up(work.at[seed_idx, "FAMILIA"]) if "FAMILIA" in work.columns else ""
    color_r = up(work.at[seed_idx, "COLOR_R"]) if "COLOR_R" in work.columns else ""
    style   = up(work.at[seed_idx, "STYLE"])   if "STYLE"   in work.columns else ""

    def f2(x):
        try: return float(x)
        except: return 0.0

    ancho_c = f2(work.at[seed_idx, "ANCHO.F.C"]) if "ANCHO.F.C" in work.columns else 0.0
    ancho_m = f2(work.at[seed_idx, "ANCHO.F.M"]) if "ANCHO.F.M" in work.columns else 0.0

    restr_fam   = params.get("RESTRICCIONES_FAMILIA",    {})
    restr_color = params.get("RESTRICCIONES_COLOR",      {})
    restr_ancho = params.get("RESTRICCIONES_ANCHO",      {})
    reglas_combo= params.get("REGLAS_ANCHOS_COMBINADOS", [])
    rule_order  = [x.strip().upper() for x in
                   norm_str(params.get("RULE_ORDER", "")).split(">") if x.strip()] or \
                  ["ANCHO18", "COMBO_ANCHOS", "COLOR_R", "FAMILIA", "DEFAULT"]

    def ancho_activo_leq_lim(ac, am, lim):
        vals = []
        try:
            if ac and not pd.isna(ac) and float(ac) > 0: vals.append(float(ac))
        except: pass
        try:
            if am and not pd.isna(am) and float(am) > 0: vals.append(float(am))
        except: pass
        return len(vals) > 0 and min(vals) <= float(lim)

    def try_ancho18():
        if style in restr_ancho:
            lim = restr_ancho[style].get("limite", None)
            pris = order_priorities(restr_ancho[style].get("prioridades", []), params)
            if lim is not None and ancho_activo_leq_lim(ancho_c, ancho_m, lim) and pris:
                rule_info.update({"regla_aplicada": "ANCHO18", "prioridades": list(pris),
                                   "limite_ancho_style": lim, "origen_prioridad": "STYLE"})
                return order_by_priorities(base, pris)

    def try_combo():
        for regla in reglas_combo:
            a1, a2 = regla["a1"], regla["a2"]
            pris = order_priorities(regla["prioridades"], params)
            seed_match = any(abs(v - a) < 1e-6
                             for v in [ancho_c, ancho_m] for a in [a1, a2])
            if not seed_match: continue
            objetivo = a2 if (abs(ancho_c-a1)<1e-6 or abs(ancho_m-a1)<1e-6) else a1
            existe = any(
                abs(f2(work.at[i, "ANCHO.F.C"]) - objetivo) < 1e-6 or
                abs(f2(work.at[i, "ANCHO.F.M"]) - objetivo) < 1e-6
                for i in work.index
                if i != seed_idx and float(work.at[i, "LBS_RESTANTES"]) > 0
            )
            if existe and pris:
                rule_info.update({"regla_aplicada": "COMBO_ANCHOS", "prioridades": list(pris),
                                   "match_combo": True, "origen_prioridad": "COMBO",
                                   "combo_target_width": float(objetivo)})
                return order_by_priorities(base, pris)

    def try_color_r():
        if color_r in restr_color and restr_color[color_r]:
            p = float(restr_color[color_r])
            rule_info.update({"regla_aplicada": "COLOR_R", "prioridades": [p], "origen_prioridad": "COLOR"})
            return order_by_priorities(base, [p])

    def try_familia():
        if fam in restr_fam and restr_fam[fam]:
            pris = order_priorities(restr_fam[fam], params)
            rule_info.update({"regla_aplicada": "FAMILIA", "prioridades": list(pris), "origen_prioridad": "FAMILIA"})
            return order_by_priorities(base, pris)

    dispatch = {"ANCHO18": try_ancho18, "COMBO_ANCHOS": try_combo,
                "COLOR_R": try_color_r, "FAMILIA": try_familia, "DEFAULT": lambda: base}
    for token in rule_order:
        fn = dispatch.get(token)
        if fn:
            out = fn()
            if out is not None: return out, rule_info
    return base, rule_info

# ============================================================
# PRIORITY MATCHING
# ============================================================
def ranges_matching_priority(pri, ranges_try, tol=1e-6, allow_nearest_higher=True):
    pri = float(pri)
    exact = [r for r in ranges_try if abs(float(r["MAXIMO"]) - pri) <= tol]
    if exact: return exact
    if not allow_nearest_higher: return []
    higher = sorted([r for r in ranges_try if float(r["MAXIMO"]) >= pri - tol],
                    key=lambda r: (float(r["MAXIMO"]) - pri, -float(r["MAXIMO"])))
    return [higher[0]] if higher else []

# ============================================================
# SCORING
# ============================================================
def score_lote(lote_dict, resumen_rows, params):
    if lote_dict is None: return -1e30
    W_FILL      = params.get("W_FILL",             5.0)
    W_CAP_LOSS  = params.get("W_CAP_LOSS",         3.0)
    W_WIDTH_PREF= params.get("W_WIDTH_PREF",       2.0)
    W_1100      = params.get("W_1100_WIDTHS_STRICT",10.0)
    pref_list   = params.get("WIDTH_PREF_LIST",    [2, 3, 1, 4, 5, 6])
    total  = float(lote_dict.get("TOTAL_LOTE", 0.0))
    maximo = float(lote_dict.get("MAXIMO", 1.0))
    fill     = total / maximo if maximo > 1e-9 else 0.0
    cap_loss = maximo - total
    anchos = {float(w) for r in resumen_rows for w in r.get("ANCHOS_ROW", []) if w is not None}
    wu = len(anchos)
    try:    rank = pref_list.index(wu)
    except: rank = len(pref_list) + abs(wu - pref_list[-1])
    score = W_FILL * fill - W_CAP_LOSS * cap_loss + W_WIDTH_PREF * (-float(rank))
    if abs(maximo - 1100.0) < 1e-6:
        score -= W_1100 * max(0, wu - 1)
    return score

def filter_ranges_for_width_target(ranges_try, mixv, width_target, params):
    mixu = str(mixv).strip().upper()
    allowed = set()
    if width_target == 3:
        allowed = params.get("ALLOWED_MAXIMO_FOR_3_WIDTHS", {}).get(mixu, set())
    elif width_target == 4:
        allowed = params.get("ALLOWED_MAXIMO_FOR_4_WIDTHS", {}).get(mixu, set())
    return [r for r in ranges_try if float(r["MAXIMO"]) in allowed] if allowed else list(ranges_try)

# ============================================================
# INTENTAR LOTE
# ============================================================
def intentar_lote_para_rango(work, seed_idx, rango, capacity_used, params, rule_info,
                              require_two_widths=False, split_min_lbs=None,
                              min_unique_widths=None, max_unique_widths=None):
    min_diff     = params["MIN_DIFF"];  max_diff  = params["MAX_DIFF"]
    max_widths   = params["MAX_WIDTHS"];max_sku   = params["MAX_SKU"]
    allowed_pairs= params["MIX_ALLOWED"]
    rid          = rango["RANGO_ID"]
    cap_left     = max(0.0, float(rango["CAPACIDAD"]) - float(capacity_used.get(rid, 0.0)))
    if cap_left <= 0: return None
    max_allowed  = min(float(rango["MAXIMO"]), cap_left)
    if float(work.at[seed_idx, "LBS_RESTANTES"]) <= 0: return None

    try:    split_min_lbs = float(split_min_lbs or params.get("SPLIT_MIN_LBS_DEFAULT", 100.0))
    except: split_min_lbs = float(params.get("SPLIT_MIN_LBS_DEFAULT", 100.0))
    allow_scrap = int(params.get("SCRAP_REMAINDER_BELOW_SPLIT_MIN", 1)) == 1

    lote_rows=[]; lote_lbs=0.0; lote_lnks=set(); lote_blocks=[]; lote_widths=[]

    def can_add_row(idx, lbs_to_add):
        if lbs_to_add <= 0: return False
        if "TONO" in work.columns:
            st = up(work.at[seed_idx,"TONO"]) if not pd.isna(work.at[seed_idx,"TONO"]) else ""
            rt = up(work.at[idx,"TONO"])      if not pd.isna(work.at[idx,"TONO"])      else ""
            if st != rt: return False
        if len(set(lote_lnks) | {work.at[idx,"LNK"]}) > max_sku: return False
        b = work.at[idx, "BLOQUE"]
        if any(not can_mix_blocks(eb, b, allowed_pairs) for eb in lote_blocks): return False
        wc = list(lote_widths) + get_row_widths(work, idx)
        if not valid_width_group(wc, min_diff, max_diff, max_widths): return False
        if max_unique_widths is not None:
            uwc = len({float(w) for w in wc if w and not pd.isna(w) and float(w)!=0.0})
            if uwc > int(max_unique_widths): return False
        return lote_lbs + lbs_to_add <= max_allowed + 1e-9

    # --- Seed ---
    seed_rest = float(work.at[seed_idx, "LBS_RESTANTES"])
    remaining = max_allowed - lote_lbs
    take = choose_take(seed_rest, remaining, split_min_lbs, allow_scrap_residue=allow_scrap)
    if take <= 0 or not can_add_row(seed_idx, take): return None

    lote_rows.append((seed_idx, take, 0.0, 0.0))
    lote_lbs  += take
    lote_lnks.add(work.at[seed_idx, "LNK"])
    lote_blocks.append(work.at[seed_idx, "BLOQUE"])
    lote_widths += get_row_widths(work, seed_idx)
    combo_target = rule_info.get("combo_target_width") if rule_info else None
    pref_list    = params.get("WIDTH_PREF_LIST", [2, 3, 1, 4, 5, 6])

    # --- Fill loop ---
    while True:
        remaining = max_allowed - lote_lbs
        if remaining <= 1e-6: break
        best=None; best_take=0.0; best_score=-1e30
        widths_now = {float(w) for w in lote_widths if w and not pd.isna(w) and float(w)!=0.0}
        n_now = len(widths_now)
        width_target = int(min_unique_widths) if min_unique_widths is not None else None

        for idx in work.index:
            rest = float(work.at[idx, "LBS_RESTANTES"])
            if rest <= 0 or any(i==idx for i,*_ in lote_rows): continue
            take = choose_take(rest, remaining, split_min_lbs, allow_scrap_residue=allow_scrap)
            if take <= 0 or not can_add_row(idx, take): continue

            widths_add   = {float(w) for w in get_row_widths(work, idx)
                            if w and not pd.isna(w) and float(w)!=0.0}
            widths_after = widths_now | widths_add
            n_after      = len(widths_after)

            fill_score  = lote_lbs + take
            width_prog  = (max(0, (width_target or 0) - n_now) -
                           max(0, (width_target or 0) - n_after)) * 500.0
            combo_hit   = 1_000.0 if combo_target and any(
                abs(float(w)-float(combo_target))<1e-6 for w in widths_add) else 0.0
            try:    pref_sc = -float(pref_list.index(n_after)) * 50.0
            except: pref_sc = -(len(pref_list) + abs(n_after - pref_list[-1])) * 50.0
            over_pen    = -2_000.0 * max(0, n_after-(width_target or 999))

            sc = fill_score + width_prog + combo_hit + pref_sc + over_pen
            if sc > best_score:
                best_score=sc; best=idx; best_take=take

        if best is None: break
        lote_rows.append((best, best_take, 0.0, 0.0))
        lote_lbs  += best_take
        lote_lnks.add(work.at[best, "LNK"])
        lote_blocks.append(work.at[best, "BLOQUE"])
        lote_widths += get_row_widths(work, best)

    if lote_lbs + 1e-9 < float(rango["MINIMO"]): return None

    # --- Validar anchos finales ---
    uw = sorted({float(w) for w in lote_widths if w and not pd.isna(w) and float(w)!=0.0})
    min_req = int(min_unique_widths) if min_unique_widths is not None else (2 if require_two_widths else None)
    if min_req is not None and len(uw) < min_req:           return None
    if max_unique_widths is not None and len(uw) > int(max_unique_widths): return None

    return {"RANGO_ID": rango["RANGO_ID"], "CATEGORIA": rango["CATEGORIA"],
            "MIX": rango["MIX"], "MINIMO": float(rango["MINIMO"]),
            "MAXIMO": float(rango["MAXIMO"]), "TOTAL_LOTE": float(lote_lbs),
            "ROWS": lote_rows, "REQUIERE_2_ANCHOS": bool(require_two_widths)}

# ============================================================
# RUN LOTEO
# ============================================================
def run_loteo(df_data, df_cap, params, progress_callback=None):
    ranges       = build_ranges(df_cap)
    capacity_used= {r["RANGO_ID"]: 0.0 for r in ranges}
    data = df_data.copy()
    data["BLOQUE"]        = data["PRIORIDAD"].apply(prioridad_bloque)
    data["LBS_RESTANTES"] = data["TOTAL"].astype(float)
    data["LBS_SCRAP"]     = 0.0
    detalle=[]; resumen=[]; lote_id_global=1
    block_order = ["VENCIDOS", "AHEAD", "AHEAD2", "OTROS"]
    group_keys  = ["TELA.CUERPO", "MIX"]
    group_keys.insert(1, "TONO" if "TONO" in data.columns else "COLOR")
    groups = list(data.groupby(group_keys).groups.items())

    for gi, (keys, grp_idx) in enumerate(groups):
        if progress_callback:
            progress_callback(gi / len(groups), f"Grupo {gi+1}/{len(groups)}…")
        work = data.loc[grp_idx].copy()
        tela, tono_or_color, mixv = keys[0], keys[1], keys[2]
        ranges_mix = [r for r in ranges if r["MIX"] == mixv]
        blocked = set()

        while True:
            work["LBS_RESTANTES"] = pd.to_numeric(work["LBS_RESTANTES"], errors="coerce").fillna(0.0)
            if (work["LBS_RESTANTES"] > 0).sum() == 0: break
            made_any = False

            for b in block_order:
                if b in blocked: continue
                cand = work[(work["BLOQUE"]==b) & (work["LBS_RESTANTES"]>0)]
                if len(cand)==0: blocked.add(b); continue

                beam_w    = int(params.get("BEAM_WIDTH", 3))
                top_seeds = cand.sort_values("LBS_RESTANTES", ascending=False).head(beam_w).index.tolist()
                best_lote=None; best_pack=None; best_score=-1e30

                for seed_idx in top_seeds:
                    ranges_try, rule_info = reorder_ranges_for_seed(ranges_mix, mixv, work, seed_idx, params)
                    if rule_info.get("regla_aplicada")=="ANCHO18" and up(mixv)=="DYE":
                        allowed = set(params.get("ANCHO18_ALLOWED_MAX_DYE", {2200.0,1100.0}))
                        if params.get("ANCHO18_ALLOW_SPILLOVER_2600",0)==1: allowed.add(2600.0)
                        ranges_try = [r for r in ranges_try if float(r["MAXIMO"]) in allowed]

                    lote=None; prioridad_obj=None
                    targets    = [int(x) for x in
                                  norm_str(params.get("WIDTHS_TARGET_ORDER","2>3>4")).split(">")
                                  if x.strip().isdigit()]
                    req_strict = int(params.get("REQUIRE_WIDTHS_STRICT",1))==1
                    pri_list   = order_priorities(rule_info.get("prioridades",[]), params)
                    use_upgrades = pri_list and int(params.get("UPGRADE_CATEGORIA",0))==1
                    pri_iter   = pri_list if (use_upgrades and int(params.get("TRY_ALL_PRIORITIES",1))==1) else [None]

                    # --- Intentos por target de anchos ---
                    for target in targets:
                        cand_all = filter_ranges_for_width_target(ranges_try, mixv, target, params)
                        found = False
                        for pri in pri_iter:
                            cands = cand_all if pri is None else \
                                ranges_matching_priority(pri, cand_all, allow_nearest_higher=True)
                            for r in cands:
                                if capacity_used[r["RANGO_ID"]] >= r["CAPACIDAD"]-1e-6: continue
                                split_min = params.get("SPLIT_MIN_LBS_ANCHO18",250) \
                                    if rule_info.get("regla_aplicada")=="ANCHO18" \
                                    else float(params.get("SPLIT_MIN_LBS_DEFAULT",100.0))
                                intento = intentar_lote_para_rango(
                                    work, seed_idx, r, capacity_used, params, rule_info,
                                    require_two_widths=(rule_info.get("regla_aplicada")=="COMBO_ANCHOS"),
                                    split_min_lbs=split_min,
                                    min_unique_widths=target,
                                    max_unique_widths=(target if req_strict else None))
                                if intento:
                                    lote=intento; prioridad_obj=float(pri) if pri else None
                                    found=True; break
                            if found: break
                        if lote: break

                    # --- Fallback sin restricción de target ---
                    if lote is None:
                        for r in ranges_try:
                            if capacity_used[r["RANGO_ID"]] >= r["CAPACIDAD"]-1e-6: continue
                            split_min = params.get("SPLIT_MIN_LBS_ANCHO18",250) \
                                if rule_info.get("regla_aplicada")=="ANCHO18" \
                                else float(params.get("SPLIT_MIN_LBS_DEFAULT",100.0))
                            intento = intentar_lote_para_rango(
                                work, seed_idx, r, capacity_used, params, rule_info,
                                require_two_widths=(rule_info.get("regla_aplicada")=="COMBO_ANCHOS"),
                                split_min_lbs=split_min)
                            if intento is None and rule_info.get("regla_aplicada")=="COMBO_ANCHOS":
                                intento = intentar_lote_para_rango(
                                    work, seed_idx, r, capacity_used, params, rule_info,
                                    require_two_widths=False, split_min_lbs=split_min)
                            if intento:
                                lote=intento; break

                    if lote:
                        rs = [{"LNK": work.at[i,"LNK"], "ANCHOS_ROW": get_row_widths(work,i)}
                              for i,*_ in lote["ROWS"]]
                        sc = score_lote({"MAXIMO":float(lote["MAXIMO"]),
                                         "TOTAL_LOTE":float(lote["TOTAL_LOTE"])}, rs, params)
                        if sc > best_score:
                            best_score=sc; best_lote=lote
                            best_pack=(lote, rule_info, prioridad_obj, best_score)

                if best_lote is None: blocked.add(b); continue

                lote, rule_info, prioridad_obj, best_score = best_pack
                split_min = params.get("SPLIT_MIN_LBS_ANCHO18",250) \
                    if rule_info.get("regla_aplicada")=="ANCHO18" \
                    else float(params.get("SPLIT_MIN_LBS_DEFAULT",100.0))
                lote_id = f"L{lote_id_global:06d}"; lote_id_global+=1

                all_w = []
                for i,*_ in lote["ROWS"]: all_w += get_row_widths(work,i)
                anchos_lote = sorted({float(w) for w in all_w if w and not pd.isna(w) and float(w)!=0.0})
                anchos_str  = str(anchos_lote)
                regla_final = rule_info.get("regla_aplicada","NONE")
                req2        = False
                if regla_final=="COMBO_ANCHOS":
                    req2 = bool(lote.get("REQUIERE_2_ANCHOS")) and len(anchos_lote)>=2
                    if not req2: regla_final="COMBO_ANCHOS_FALLBACK"

                for idx, lbs_asig, oe, us in lote["ROWS"]:
                    detalle.append({
                        "LOTE_ID": lote_id, "ANCHOS_LOTE": anchos_str,
                        "CATEGORIA": lote["CATEGORIA"], "MIX": lote["MIX"],
                        "TELA.CUERPO": tela, "COLOR": work.at[idx,"COLOR"],
                        "TONO": work.at[idx,"TONO"] if "TONO" in work.columns else "",
                        "LNK": work.at[idx,"LNK"], "PRIORIDAD": work.at[idx,"PRIORIDAD"],
                        "BLOQUE": work.at[idx,"BLOQUE"],
                        "ANCHO.F.C": float(work.at[idx,"ANCHO.F.C"]),
                        "ANCHO.F.M": float(work.at[idx,"ANCHO.F.M"]),
                        "CONSUMO_C": float(work.at[idx,"CONSUMO_C"]),
                        "FAMILIA": work.at[idx,"FAMILIA"],
                        "COLOR_R": work.at[idx,"COLOR_R"],
                        "STYLE":   work.at[idx,"STYLE"],
                        "LBS_ASIGNADAS": float(lbs_asig),
                        "APLICA_REGLA": regla_final,
                        "PRIORIDAD_USADA": float(lote["MAXIMO"]),
                        "PRIORIDAD_OBJETIVO": prioridad_obj,
                        "REQUIERE_2_ANCHOS": bool(req2),
                        "DECISION_SCORE": float(best_score),
                    })
                    work.at[idx,"LBS_RESTANTES"] = max(0.0, float(work.at[idx,"LBS_RESTANTES"]) - float(lbs_asig))
                    rem = float(work.at[idx,"LBS_RESTANTES"])
                    if rem > 1e-9 and rem+1e-9 < float(split_min):
                        work.at[idx,"LBS_SCRAP"]    += rem
                        work.at[idx,"LBS_RESTANTES"] = 0.0

                bloques = [d["BLOQUE"] for d in detalle if d["LOTE_ID"]==lote_id]
                resumen.append({
                    "LOTE_ID": lote_id, "ANCHOS_LOTE": anchos_str,
                    "CATEGORIA": lote["CATEGORIA"], "MIX": lote["MIX"],
                    "TELA.CUERPO": tela, "COLOR_TONO": tono_or_color,
                    "LBS_TOTAL": float(lote["TOTAL_LOTE"]),
                    "MIN_RANGO": float(lote["MINIMO"]), "MAX_RANGO": float(lote["MAXIMO"]),
                    "CAPACIDAD_PERDIDA": float(lote["MAXIMO"]-lote["TOTAL_LOTE"]),
                    "SKU_DISTINTOS": len({d["LNK"] for d in detalle if d["LOTE_ID"]==lote_id}),
                    "ANCHOS_UNICOS": len(anchos_lote),
                    "BLOQUE_DOMINANTE": max(set(bloques), key=bloques.count) if bloques else "",
                    "REGLA_DOMINANTE": regla_final,
                    "PRIORIDAD_FINAL": float(lote["MAXIMO"]),
                })
                capacity_used[lote["RANGO_ID"]] += float(lote["TOTAL_LOTE"])
                blocked=set(); made_any=True; break

            if not made_any: break

        data.loc[work.index,"LBS_RESTANTES"] = work["LBS_RESTANTES"]
        data.loc[work.index,"LBS_SCRAP"]     = work["LBS_SCRAP"]

    if progress_callback: progress_callback(1.0, "¡Listo!")

    exced_cols = ["LNK","TELA.CUERPO","COLOR","MIX","PRIORIDAD","BLOQUE",
                  "ANCHO.F.C","ANCHO.F.M","TOTAL","LBS_RESTANTES","LBS_SCRAP"]
    if "TONO" in data.columns: exced_cols.insert(3,"TONO")
    exced = data[data["LBS_RESTANTES"]>1e-9][exced_cols].copy()

    df_det = pd.DataFrame(detalle)
    if len(df_det) > 0:
        df_det["DOCENAS"] = np.where(df_det["CONSUMO_C"]>0,
                                      df_det["LBS_ASIGNADAS"]/df_det["CONSUMO_C"], np.nan)
    df_res = pd.DataFrame(resumen)
    return df_det, df_res, exced

# ============================================================
# REPORTS
# ============================================================
def build_reports(df_data, df_cap, df_det, df_res):
    df_cap_s = df_cap[["CATEGORIA","MIX","MINIMO","MAXIMO","CAPACIDAD"]].copy()
    agg = df_det.groupby(["CATEGORIA","MIX"],as_index=False)["LBS_ASIGNADAS"].sum() \
        if len(df_det)>0 else pd.DataFrame({"CATEGORIA":[],"MIX":[],"LBS_ASIGNADAS":[]})
    df_cc = df_cap_s.merge(agg,on=["CATEGORIA","MIX"],how="left").fillna({"LBS_ASIGNADAS":0.0})
    df_cc["DIFERENCIA"] = df_cc["LBS_ASIGNADAS"] - df_cc["CAPACIDAD"]
    df_cc = df_cc.sort_values(["MIX","CATEGORIA"])

    df_data2 = df_data.copy()
    df_data2["BLOQUE"] = df_data2["PRIORIDAD"].apply(prioridad_bloque)
    prio_base = df_data2.groupby(["MIX","BLOQUE"],as_index=False)["TOTAL"].sum().rename(columns={"TOTAL":"LBS_BASE"})
    prio_asig = df_det.groupby(["MIX","BLOQUE"],as_index=False)["LBS_ASIGNADAS"].sum() \
        if len(df_det)>0 else pd.DataFrame({"MIX":[],"BLOQUE":[],"LBS_ASIGNADAS":[]})
    prio_vs = prio_base.merge(prio_asig,on=["MIX","BLOQUE"],how="left").fillna({"LBS_ASIGNADAS":0.0})
    prio_vs["LBS_SIN_ASIGNAR"] = prio_vs["LBS_BASE"] - prio_vs["LBS_ASIGNADAS"]
    ob = ["VENCIDOS","AHEAD","AHEAD2","OTROS"]
    prio_vs["_ord"] = prio_vs["BLOQUE"].apply(lambda x: ob.index(x) if x in ob else 99)
    prio_vs = prio_vs.sort_values(["MIX","_ord"]).drop(columns=["_ord"])

    lnk_base = df_data.groupby(["MIX","LNK"],as_index=False)["TOTAL"].sum().rename(columns={"TOTAL":"LBS_BASE"})
    lnk_scrap= df_data.groupby(["MIX","LNK"],as_index=False)["LBS_SCRAP"].sum() \
        if "LBS_SCRAP" in df_data.columns else pd.DataFrame({"MIX":[],"LNK":[],"LBS_SCRAP":[]})
    lnk_asig = df_det.groupby(["MIX","LNK"],as_index=False)["LBS_ASIGNADAS"].sum() \
        if len(df_det)>0 else pd.DataFrame({"MIX":[],"LNK":[],"LBS_ASIGNADAS":[]})
    lnk_comp = (lnk_base.merge(lnk_asig,on=["MIX","LNK"],how="left")
                         .merge(lnk_scrap,on=["MIX","LNK"],how="left")
                         .fillna({"LBS_ASIGNADAS":0.0,"LBS_SCRAP":0.0}))
    lnk_comp["BALANCE"] = lnk_comp["LBS_BASE"]-lnk_comp["LBS_ASIGNADAS"]-lnk_comp["LBS_SCRAP"]
    lnk_comp["ESTADO"]  = np.where(lnk_comp["BALANCE"].abs()<=1e-6,
                                    np.where(lnk_comp["LBS_SCRAP"]>1e-6,"COMPLETO (SCRAP)","COMPLETO"),
                                    "INCOMPLETO")
    lnk_comp = lnk_comp.sort_values(["MIX","ESTADO","BALANCE"],ascending=[True,True,False])

    return {"CAPACIDAD_X_CATEG": df_cc,
            "PRIORIDAD_VS_ASIG": prio_vs,
            "LNK_COMPLETITUD":   lnk_comp}

# ============================================================
# EXPORTAR EXCEL
# ============================================================
def exportar_excel(df_det, df_res, df_exced, reports):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_det.to_excel(w,  index=False, sheet_name="DETALLE_LOTES")
        df_res.to_excel(w,  index=False, sheet_name="RESUMEN_LOTES")
        df_exced.to_excel(w,index=False, sheet_name="EXCEDENTES")
        reports["CAPACIDAD_X_CATEG"].to_excel(w, index=False, sheet_name="CAPACIDAD_X_CATEG")
        reports["PRIORIDAD_VS_ASIG"].to_excel(w, index=False, sheet_name="PRIORIDAD_VS_ASIG")
        reports["LNK_COMPLETITUD"].to_excel(w,   index=False, sheet_name="LNK_COMPLETITUD")
    buf.seek(0)
    return buf.read()

# ============================================================
# STREAMLIT UI
# ============================================================
with st.sidebar:
    st.header("📂 Archivo")
    uploaded = st.file_uploader("Sube tu .xlsx con la hoja DATA", type=["xlsx","xlsm"])

    st.markdown("---")
    st.header("⚙️ Parámetros")

    st.subheader("Rangos (Máximos permitidos)")
    st.caption("Editar CAPACIDADES_DEFAULT en el código para cambiar rangos y capacidades.")

    st.subheader("Anchos")
    min_diff   = st.number_input("Diff. mínima entre anchos", value=0.0,  step=0.5)
    max_diff   = st.number_input("Diff. máxima entre anchos", value=6.0,  step=0.5)
    max_widths = st.number_input("Max anchos únicos por lote", value=6,    step=1, min_value=1)

    st.subheader("Objetivo de anchos")
    widths_target_order = st.text_input("Orden preferido (ej. 2>3>4)", value="2>3>4")
    require_strict      = st.checkbox("Forzar estrictamente el target", value=True)
    allowed_3w_dye_str  = st.text_input("Máximos permitidos para 3 anchos DYE (coma)", value="2200,2600")
    allowed_4w_dye_str  = st.text_input("Máximos permitidos para 4 anchos DYE (coma)", value="2600")

    def parse_set(s):
        parts = re.split(r"[;,\s]+", s.strip())
        vals = []
        for p in parts:
            try: vals.append(float(p))
            except: pass
        return vals

    st.subheader("SKU y splits")
    max_sku          = st.number_input("Max SKUs por lote",              value=6,   step=1, min_value=1)
    split_min_default= st.number_input("Split mínimo LBS (default)",     value=100.0, step=10.0)
    split_min_ancho18= st.number_input("Split mínimo LBS (ANCHO18)",     value=250.0, step=10.0)

    st.subheader("Búsqueda")
    beam_width = st.slider("Beam Width (seeds por bloque)", 1, 10, 3)

    ui_params = {
        "min_diff":              min_diff,
        "max_diff":              max_diff,
        "max_widths":            int(max_widths),
        "max_sku":               int(max_sku),
        "widths_target_order":   widths_target_order,
        "require_strict":        require_strict,
        "allowed_3w_dye":        parse_set(allowed_3w_dye_str),
        "allowed_4w_dye":        parse_set(allowed_4w_dye_str),
        "split_min_default":     split_min_default,
        "split_min_ancho18":     split_min_ancho18,
        "beam_width":            beam_width,
    }

if uploaded is None:
    st.info("👈 Sube tu archivo Excel con la hoja DATA para comenzar.")
    st.stop()

file_bytes = uploaded.read()

if st.button("🚀 Ejecutar Loteo", type="primary", use_container_width=True):
    progress_bar = st.progress(0, text="Iniciando…")
    try:
        def upd(pct, msg): progress_bar.progress(min(pct,1.0), text=msg)

        with st.spinner("Cargando DATA…"):
            df_data, hdr_row = load_data(io.BytesIO(file_bytes))
        st.success(f"✅ {len(df_data):,} filas cargadas (header fila {hdr_row+1})")

        df_cap  = make_df_cap()
        params  = build_params(ui_params)

        df_det, df_res, df_exced = run_loteo(df_data, df_cap, params, progress_callback=upd)

        progress_bar.progress(1.0, text="Construyendo reportes…")
        reports    = build_reports(df_data, df_cap, df_det, df_res)
        xlsx_bytes = exportar_excel(df_det, df_res, df_exced, reports)

        st.session_state["res"] = {
            "df_det": df_det, "df_res": df_res, "df_exced": df_exced,
            "reports": reports, "xlsx_bytes": xlsx_bytes,
        }
        progress_bar.empty()
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ {e}")
        st.exception(e)

if "res" in st.session_state:
    r = st.session_state["res"]
    df_det=r["df_det"]; df_res=r["df_res"]; df_exced=r["df_exced"]; reports=r["reports"]

    st.markdown("---")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🗂️ Lotes",           f"{len(df_res):,}")
    c2.metric("⚖️ LBS asignadas",   f"{df_det['LBS_ASIGNADAS'].sum():,.0f}" if len(df_det)>0 else "0")
    c3.metric("⚠️ Excedentes",      f"{len(df_exced):,}")
    c4.metric("📉 Cap. perdida",     f"{df_res['CAPACIDAD_PERDIDA'].sum():,.0f} lbs" if len(df_res)>0 else "0")

    st.download_button("📥 Descargar RESULTADOS_LOTES.xlsx", data=r["xlsx_bytes"],
                       file_name="RESULTADOS_LOTES.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True, type="primary")

    tab1,tab2,tab3,tab4,tab5 = st.tabs([
        "📋 Resumen","🔍 Detalle","⚠️ Excedentes","📊 Capacidad x Categ.","✅ LNK Completitud"])

    with tab1:
        st.dataframe(df_res, use_container_width=True, height=450)

    with tab2:
        mix_opts = ["Todos"] + sorted(df_det["MIX"].unique().tolist()) if len(df_det)>0 else ["Todos"]
        mix_sel  = st.selectbox("Filtrar por MIX", mix_opts)
        show = df_det if mix_sel=="Todos" else df_det[df_det["MIX"]==mix_sel]
        st.dataframe(show, use_container_width=True, height=450)

    with tab3:
        if len(df_exced)>0:
            st.warning(f"{len(df_exced)} filas sin asignar.")
            st.dataframe(df_exced, use_container_width=True)
        else:
            st.success("🎉 Sin excedentes.")

    with tab4:
        st.dataframe(reports["CAPACIDAD_X_CATEG"].style.background_gradient(
            subset=["LBS_ASIGNADAS"], cmap="Greens"), use_container_width=True)

    with tab5:
        cmap = {"COMPLETO":"background-color:#d4edda",
                "COMPLETO (SCRAP)":"background-color:#fff3cd",
                "INCOMPLETO":"background-color:#f8d7da"}
        def hl(row): return [cmap.get(row["ESTADO"],"")] * len(row)
        st.dataframe(reports["LNK_COMPLETITUD"].style.apply(hl, axis=1), use_container_width=True)
