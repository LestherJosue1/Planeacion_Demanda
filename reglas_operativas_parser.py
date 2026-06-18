# ============================================
# reglas_operativas_parser.py
# Parser robusto de la hoja REGLAS_OPERATIVAS (formato semi-libre) hacia
# una estructura `params` editable desde la UI de Streamlit.
# ============================================

import re
import pandas as pd
import numpy as np

DEFAULT_MAX_WIDTHS_BY_CAT = {
    "A-4000": 4, "B-3300": 4,
    "C-2600": 3, "D-2200": 3, "F-2200": 3,
    "E-1100": 2, "G-1100": 2,
}

# Pares de bloques permitidos para mezclar en un mismo lote, según
# COMBINACION_PRIORIDAD: PAST DUE+DUE(VENCIDOS), +AHEAD, AHEAD+AHEAD2, OTROS solo con AHEAD2.
DEFAULT_ALLOWED_PAIRS = [
    ("VENCIDOS", "VENCIDOS"),
    ("VENCIDOS", "AHEAD"),
    ("AHEAD", "AHEAD"),
    ("AHEAD", "AHEAD2"),
    ("OTROS", "AHEAD2"),
]

RULE_TOKENS = ["ANCHO18", "COMBO_ANCHOS", "COLOR_R", "FAMILIA"]


def _num(x, default=None):
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return default
        return float(x)
    except Exception:
        return default


def _first_number_in_text(text, default=None):
    if not text:
        return default
    m = re.search(r"(\d+(\.\d+)?)", str(text))
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return default
    return default


def find_reglas_operativas_table(xlsm_path):
    """Localiza la fila de encabezado REGLAS/PRODUCTO/CLAVE1.../OBSERVACION
    dentro de la hoja REGLAS_OPERATIVAS (puede no estar en la fila 1)."""
    raw = pd.read_excel(xlsm_path, sheet_name="REGLAS_OPERATIVAS", engine="openpyxl", header=None)
    header_row = None
    for r in range(min(20, len(raw))):
        vals = [str(v).strip().upper() if pd.notna(v) else "" for v in raw.iloc[r].tolist()]
        if "REGLAS" in vals and "PRODUCTO" in vals:
            header_row = r
            break
    if header_row is None:
        raise ValueError("No se encontró la fila de encabezado (REGLAS/PRODUCTO/CLAVE1...) en REGLAS_OPERATIVAS.")
    return raw, header_row


def parse_reglas_operativas(xlsm_path):
    """Lee la hoja REGLAS_OPERATIVAS y construye:
      - reglas_raw: lista de dicts (cada fila tal cual, para mostrar como referencia en la UI)
      - params_default: dict con la estructura `params` por defecto, lista para edición en Streamlit
      - df_cap_default: DataFrame con la sub-tabla CAPACIDAD TINTORERIA
    """
    raw, header_row = find_reglas_operativas_table(xlsm_path)
    cols = [str(v).strip().upper() if pd.notna(v) else "" for v in raw.iloc[header_row].tolist()]
    body = raw.iloc[header_row + 1:].copy()
    body.columns = cols[:len(body.columns)]

    # localizar dónde empieza la sub-tabla CAPACIDAD TINTORERIA (columna REGLAS == 'CAPACIDAD TINTORERIA')
    if "REGLAS" not in body.columns:
        raise ValueError("La hoja REGLAS_OPERATIVAS no tiene columna REGLAS reconocible.")

    cap_mask = body["REGLAS"].astype(str).str.strip().str.upper() == "CAPACIDAD TINTORERIA"
    cap_rows = body[cap_mask]
    rules_rows = body[~cap_mask & body["REGLAS"].notna() & (body["REGLAS"].astype(str).str.strip() != "")]

    # ---------- Reglas con tabla (RESTRICCION_FAMILIA / COLOR / ANCHO) ----------
    restr_fam = {}
    restr_color = {}
    restr_ancho = {}
    reglas_raw = []

    obs_minimo_ancho = None
    obs_maximo_ancho = None
    obs_max_skus = None
    obs_split_minimo = None

    for _, r in rules_rows.iterrows():
        tag = str(r.get("REGLAS", "")).strip().upper()
        producto = str(r.get("PRODUCTO", "")).strip().upper() if pd.notna(r.get("PRODUCTO", None)) else ""
        c1 = _num(r.get("CLAVE1", None))
        c2 = _num(r.get("CLAVE2", None))
        c3 = _num(r.get("CLAVE3", None))
        c4 = _num(r.get("CLAVE4", None))
        obs = str(r.get("OBSERVACION", "")).strip() if pd.notna(r.get("OBSERVACION", None)) else ""

        reglas_raw.append({
            "REGLAS": tag, "PRODUCTO": producto,
            "CLAVE1": c1, "CLAVE2": c2, "CLAVE3": c3, "CLAVE4": c4,
            "OBSERVACION": obs
        })

        if tag == "RESTRICCION_FAMILIA" and producto:
            caps = [v for v in [c1, c2, c3, c4] if v is not None]
            if caps:
                restr_fam[producto] = caps

        elif tag == "RESTRICCION_COLOR" and producto:
            # aplica a TODOS -> se guarda bajo clave especial; la UI puede expandir a colores reales
            if c1 is not None:
                restr_color[producto] = c1

        elif tag == "RESTRICCION_ANCHO" and producto:
            if c1 is not None:
                restr_ancho[producto] = {"limite": c1, "prioridades": [c2] if c2 is not None else []}

        elif tag == "MINIMO ANCHO":
            obs_minimo_ancho = _first_number_in_text(obs, 1.0)

        elif tag == "MAXIMO ANCHO":
            obs_maximo_ancho = _first_number_in_text(obs, 6.0)

        elif tag == "MAXIMO SKUS":
            obs_max_skus = _first_number_in_text(obs, 6.0)

        elif tag == "SPLIT_MINIMO":
            obs_split_minimo = _first_number_in_text(obs, 500.0)

    # ---------- Sub-tabla CAPACIDAD TINTORERIA ----------
    # En la plantilla real, la fila de encabezado de esta sub-tabla está embebida
    # (columna PRODUCTO=CATEGORIA, CLAVE1=MINIMO, CLAVE2=MAXIMO, CLAVE3=CAPACIDAD, CLAVE4=MIX)
    cap_data_rows = cap_rows[cap_rows["PRODUCTO"].notna() & (cap_rows["PRODUCTO"].astype(str).str.strip().str.upper() != "CATEGORIA")]
    cap_records = []
    for _, r in cap_data_rows.iterrows():
        categoria = str(r.get("PRODUCTO", "")).strip()
        if not categoria:
            continue
        minimo = _num(r.get("CLAVE1", None))
        maximo = _num(r.get("CLAVE2", None))
        capacidad = _num(r.get("CLAVE3", None))
        mix = str(r.get("CLAVE4", "")).strip().upper() if pd.notna(r.get("CLAVE4", None)) else ""
        if minimo is None or maximo is None or capacidad is None or not mix:
            continue
        cap_records.append({
            "CATEGORIA": categoria, "MINIMO": minimo, "MAXIMO": maximo,
            "CAPACIDAD": capacidad, "MIX": mix
        })

    if not cap_records:
        # fallback a los valores conocidos de la plantilla, por si el parseo posicional falla
        cap_records = [
            {"CATEGORIA": "A-4000", "MINIMO": 3900, "MAXIMO": 4000, "CAPACIDAD": 660000, "MIX": "DYE"},
            {"CATEGORIA": "B-3300", "MINIMO": 3000, "MAXIMO": 3300, "CAPACIDAD": 555000, "MIX": "DYE"},
            {"CATEGORIA": "C-2600", "MINIMO": 2500, "MAXIMO": 2600, "CAPACIDAD": 1967000, "MIX": "DYE"},
            {"CATEGORIA": "D-2200", "MINIMO": 2000, "MAXIMO": 2200, "CAPACIDAD": 640000, "MIX": "DYE"},
            {"CATEGORIA": "E-1100", "MINIMO": 1000, "MAXIMO": 1100, "CAPACIDAD": 437000, "MIX": "DYE"},
            {"CATEGORIA": "F-2200", "MINIMO": 2000, "MAXIMO": 2200, "CAPACIDAD": 1212000, "MIX": "BLEACH"},
            {"CATEGORIA": "G-1100", "MINIMO": 1000, "MAXIMO": 1100, "CAPACIDAD": 75000, "MIX": "BLEACH"},
        ]

    df_cap_default = pd.DataFrame(cap_records)

    # ---------- Construcción de params por defecto ----------
    params_default = {
        "MIN_DIFF": obs_minimo_ancho if obs_minimo_ancho is not None else 1.0,
        "MAX_DIFF": obs_maximo_ancho if obs_maximo_ancho is not None else 6.0,
        "MAX_SKU": int(obs_max_skus) if obs_max_skus is not None else 6,
        "MAX_WIDTHS_BY_CAT": dict(DEFAULT_MAX_WIDTHS_BY_CAT),
        "MAX_WIDTHS_DEFAULT": 4,

        "SPLIT_MIN_LBS_DEFAULT": obs_split_minimo if obs_split_minimo is not None else 500.0,
        "SPLIT_MIN_LBS_ANCHO18": 250.0,
        "SCRAP_REMAINDER_BELOW_SPLIT_MIN": 1,

        "RESTRICCIONES_FAMILIA": restr_fam,
        "RESTRICCIONES_COLOR": restr_color,
        "RESTRICCIONES_ANCHO": restr_ancho,
        "REGLAS_ANCHOS_COMBINADOS": [],  # no viene en la nueva plantilla; queda vacío por defecto, editable

        "ALLOWED_PAIRS": list(DEFAULT_ALLOWED_PAIRS),
        "MIX_ALLOWED": set(DEFAULT_ALLOWED_PAIRS) | {(b, a) for a, b in DEFAULT_ALLOWED_PAIRS},

        "RULE_ORDER": "ANCHO18>COMBO_ANCHOS>COLOR_R>FAMILIA>DEFAULT",
        "PRIORITY_ORDER": "",

        "APPLY_RULES_BLEACH": 0,  # MIX-BLEACH-DYE: en BLEACH NO aplican RESTRICCION_FAMILIA/COLOR

        "UPGRADE_CATEGORIA": 1,
        "TRY_ALL_PRIORITIES": 1,

        "ANCHO18_ALLOW_SPILLOVER_2600": 0,
        "ANCHO18_ALLOWED_MAX_DYE": {2200.0, 1100.0},

        "BEAM_WIDTH": 3,
        "W_FILL": 5.0,
        "W_CAP_LOSS": 3.0,
        "WIDTH_PREF_LIST": [2, 3, 1, 4, 5, 6],
        "W_WIDTH_PREF": 2.0,
        "W_1100_WIDTHS_STRICT": 10.0,

        "WIDTHS_TARGET_ORDER": "2>3>4",
        "REQUIRE_WIDTHS_STRICT": 1,
        "ALLOWED_MAXIMO_FOR_3_WIDTHS": {"DYE": {2200.0, 2600.0}, "BLEACH": set()},
        "ALLOWED_MAXIMO_FOR_4_WIDTHS": {"DYE": {2600.0}, "BLEACH": set()},

        # TIPO_TEJIDO (nuevo)
        "TIPO_TEJIDO_ENABLE": 1,
        "TIPO_TEJIDO_CATEGORIAS": ["A-4000", "B-3300"],
        "W_TIPO_TEJIDO_FLEECE": 4.0,

        # Activación individual de cada regla (toggles UI)
        "RULE_TOGGLES": {
            "RESTRICCION_FAMILIA": True,
            "RESTRICCION_COLOR": True,
            "RESTRICCION_ANCHO": True,
            "MIN_MAX_ANCHO": True,
            "MAX_CANTIDAD_ANCHOS": True,
            "MAX_SKUS": True,
            "COMBINACION_PRIORIDAD": True,
            "SPLIT_MINIMO": True,
            "MIX_BLEACH_DYE": True,
            "TIPO_TEJIDO": True,
            "PCT_CARGA": True,
        },
    }

    return reglas_raw, params_default, df_cap_default


def rule_order_options():
    """Todas las combinaciones posibles (permutaciones) de las 4 reglas + DEFAULT al final,
    para el selector de escenarios de ORDEN_REGLAS."""
    from itertools import permutations
    return [">".join(p) + ">DEFAULT" for p in permutations(RULE_TOKENS)]
