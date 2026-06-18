# ============================================
# app.py — App Streamlit de Loteo de Tintorería (NV2)
# ============================================
import io
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from loteo_engine import (
    load_data_sheet, build_cap_dataframe, run_loteo, build_reports,
    format_workbook, all_rule_order_options, prioridad_bloque
)
from reglas_operativas_parser import parse_reglas_operativas, rule_order_options

st.set_page_config(page_title="Loteo de Tintorería NV2", layout="wide")
st.title("🧵 Loteo de Tintorería — NV2")

# ---------------------------- Estado ----------------------------
for key, default in [
    ("df_data", None), ("df_fam", None), ("reglas_raw", None),
    ("params", None), ("df_cap", None), ("excel_path", None),
    ("resultado", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def reset_params_from_excel():
    reglas_raw, params_default, df_cap_default = parse_reglas_operativas(st.session_state["excel_path"])
    st.session_state["reglas_raw"] = reglas_raw
    st.session_state["params"] = params_default
    st.session_state["df_cap"] = df_cap_default


# ---------------------------- 1. Carga de datos ----------------------------
st.header("1. Cargar Excel (DATA + REGLAS_OPERATIVAS + FAMILIA)")
uploaded = st.file_uploader("Sube el archivo .xlsx", type=["xlsx", "xlsm"])

if uploaded is not None:
    if st.session_state["excel_path"] != uploaded.name or st.session_state["df_data"] is None:
        # Guardar a disco temporalmente (pandas/openpyxl necesitan ruta o buffer)
        tmp_path = f"/tmp/{uploaded.name}"
        with open(tmp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.session_state["excel_path"] = tmp_path
        try:
            df_data, hdr_row = load_data_sheet(tmp_path)
            st.session_state["df_data"] = df_data
            st.success(f"✅ Hoja DATA leída correctamente. Encabezado detectado en fila {hdr_row+1}. {len(df_data)} filas, {len(df_data.columns)} columnas.")
        except Exception as e:
            st.error(f"❌ Error leyendo DATA: {e}")
            st.session_state["df_data"] = None

        try:
            reset_params_from_excel()
            st.success("✅ REGLAS_OPERATIVAS parseado correctamente y cargado como configuración default.")
        except Exception as e:
            st.error(f"❌ Error parseando REGLAS_OPERATIVAS: {e}")

        try:
            df_fam = pd.read_excel(tmp_path, sheet_name="FAMILIA", engine="openpyxl")
            st.session_state["df_fam"] = df_fam
        except Exception:
            st.session_state["df_fam"] = pd.DataFrame()

if st.session_state["df_data"] is not None:
    with st.expander("👀 Preview de DATA", expanded=False):
        st.dataframe(st.session_state["df_data"].head(50), use_container_width=True)
        faltantes = [c for c in ["TONO", "TIPO_TEJIDO", "PCT_CARGA"] if c not in st.session_state["df_data"].columns]
        if faltantes:
            st.warning(f"⚠️ Columnas opcionales no encontradas (se usará default): {faltantes}")

if st.session_state["params"] is None:
    st.info("Sube un archivo Excel para continuar.")
    st.stop()

params = st.session_state["params"]
df_cap = st.session_state["df_cap"]

# ---------------------------- 2. Panel de configuración ----------------------------
st.header("2. Configuración (editable)")

col_reset, col_profile_exp, col_profile_imp = st.columns(3)
with col_reset:
    if st.button("🔄 Restaurar valores del Excel"):
        reset_params_from_excel()
        st.rerun()
with col_profile_exp:
    profile_json = json.dumps({k: (list(v) if isinstance(v, set) else v) for k, v in params.items()}, default=str, indent=2)
    st.download_button("💾 Exportar perfil (JSON)", data=profile_json, file_name="perfil_loteo.json", mime="application/json")
with col_profile_imp:
    profile_file = st.file_uploader("📂 Cargar perfil (JSON)", type=["json"], key="profile_uploader")
    if profile_file is not None:
        loaded = json.load(profile_file)
        st.session_state["params"].update(loaded)
        st.success("Perfil cargado. Revisa los valores abajo.")
        params = st.session_state["params"]

tabs = st.tabs([
    "RESTRICCION_FAMILIA", "RESTRICCION_COLOR", "RESTRICCION_ANCHO",
    "ANCHOS (MIN/MAX/CANTIDAD)", "MAX_SKUS", "COMBINACION_PRIORIDAD",
    "SPLIT_MINIMO", "MIX-BLEACH-DYE", "TIPO_TEJIDO", "%CARGA",
    "ORDEN_REGLAS", "CAPACIDAD TINTORERIA", "Avanzado"
])

# --- RESTRICCION_FAMILIA ---
with tabs[0]:
    st.markdown("La restricción de familia aplica a las familias seleccionadas y se hará en las categorías seleccionadas (MAXIMO) y hacia abajo.")
    on = st.checkbox("Activar RESTRICCION_FAMILIA", value=params["RULE_TOGGLES"]["RESTRICCION_FAMILIA"], key="t_fam")
    params["RULE_TOGGLES"]["RESTRICCION_FAMILIA"] = on
    fam_rows = [{"FAMILIA": k, "MAXIMOS_PERMITIDOS": ",".join(str(int(x)) for x in v)} for k, v in params["RESTRICCIONES_FAMILIA"].items()]
    df_fam_edit = st.data_editor(pd.DataFrame(fam_rows), num_rows="dynamic", use_container_width=True, key="ed_fam")
    new_restr_fam = {}
    for _, r in df_fam_edit.iterrows():
        fam = str(r.get("FAMILIA", "")).strip().upper()
        if not fam:
            continue
        try:
            vals = [float(x.strip()) for x in str(r.get("MAXIMOS_PERMITIDOS", "")).split(",") if x.strip()]
        except Exception:
            vals = []
        if vals:
            new_restr_fam[fam] = vals
    params["RESTRICCIONES_FAMILIA"] = new_restr_fam if on else {}

# --- RESTRICCION_COLOR ---
with tabs[1]:
    st.markdown("La restricción de color aplica a todos los estilos (TODOS), en la categoría seleccionada (MAXIMO) y hacia abajo.")
    on = st.checkbox("Activar RESTRICCION_COLOR", value=params["RULE_TOGGLES"]["RESTRICCION_COLOR"], key="t_color")
    params["RULE_TOGGLES"]["RESTRICCION_COLOR"] = on
    default_cap = params["RESTRICCIONES_COLOR"].get("TODOS", 2600.0)
    cap_val = st.number_input("MAXIMO de categoría para todos los COLOR_R", value=float(default_cap), step=100.0, key="color_cap")
    if on and st.session_state["df_data"] is not None and "COLOR_R" in st.session_state["df_data"].columns:
        colores = sorted([c for c in st.session_state["df_data"]["COLOR_R"].unique() if c])
        params["RESTRICCIONES_COLOR"] = {c: cap_val for c in colores}
        st.caption(f"Se aplicará a {len(colores)} valores distintos de COLOR_R encontrados en DATA: {colores[:10]}{'...' if len(colores) > 10 else ''}")
    else:
        params["RESTRICCIONES_COLOR"] = {}

# --- RESTRICCION_ANCHO ---
with tabs[2]:
    st.markdown("Por estilo (STYLE): límite de ancho (pulgadas) y categoría (MAXIMO) asociada, hacia abajo.")
    on = st.checkbox("Activar RESTRICCION_ANCHO", value=params["RULE_TOGGLES"]["RESTRICCION_ANCHO"], key="t_ancho")
    params["RULE_TOGGLES"]["RESTRICCION_ANCHO"] = on
    ancho_rows = [{"STYLE": k, "LIMITE_ANCHO": v["limite"], "MAXIMO_CATEGORIA": ",".join(str(int(x)) for x in v["prioridades"])} for k, v in params["RESTRICCIONES_ANCHO"].items()]
    df_ancho_edit = st.data_editor(pd.DataFrame(ancho_rows), num_rows="dynamic", use_container_width=True, key="ed_ancho")
    new_restr_ancho = {}
    for _, r in df_ancho_edit.iterrows():
        style = str(r.get("STYLE", "")).strip().upper()
        if not style:
            continue
        try:
            lim = float(r.get("LIMITE_ANCHO"))
        except Exception:
            continue
        try:
            caps = [float(x.strip()) for x in str(r.get("MAXIMO_CATEGORIA", "")).split(",") if x.strip()]
        except Exception:
            caps = []
        new_restr_ancho[style] = {"limite": lim, "prioridades": caps}
    params["RESTRICCIONES_ANCHO"] = new_restr_ancho if on else {}

# --- MINIMO/MAXIMO/CANTIDAD ANCHO ---
with tabs[3]:
    on = st.checkbox("Activar reglas de MIN/MAX/CANTIDAD de anchos", value=params["RULE_TOGGLES"]["MIN_MAX_ANCHO"], key="t_minmax")
    params["RULE_TOGGLES"]["MIN_MAX_ANCHO"] = on
    c1, c2 = st.columns(2)
    with c1:
        params["MIN_DIFF"] = st.number_input("MINIMO ANCHO (pulgadas, diferencia mínima entre anchos)", value=float(params["MIN_DIFF"]), step=0.5)
    with c2:
        params["MAX_DIFF"] = st.number_input("MAXIMO ANCHO (pulgadas, diferencia máxima al mínimo)", value=float(params["MAX_DIFF"]), step=0.5)

    st.markdown("**MAXIMO CANTIDAD ANCHOS por categoría de tintorería** (reemplaza el máximo global):")
    params["RULE_TOGGLES"]["MAX_CANTIDAD_ANCHOS"] = st.checkbox("Activar MAXIMO CANTIDAD ANCHOS por categoría", value=params["RULE_TOGGLES"]["MAX_CANTIDAD_ANCHOS"], key="t_maxcant")
    cat_widths_rows = [{"CATEGORIA": k, "MAX_ANCHOS": v} for k, v in params["MAX_WIDTHS_BY_CAT"].items()]
    df_catw = st.data_editor(pd.DataFrame(cat_widths_rows), use_container_width=True, key="ed_catw")
    if params["RULE_TOGGLES"]["MAX_CANTIDAD_ANCHOS"]:
        params["MAX_WIDTHS_BY_CAT"] = {str(r["CATEGORIA"]): int(r["MAX_ANCHOS"]) for _, r in df_catw.iterrows() if str(r["CATEGORIA"]).strip()}
    else:
        params["MAX_WIDTHS_BY_CAT"] = {k: 6 for k in params["MAX_WIDTHS_BY_CAT"]}  # sin restricción real

# --- MAX SKUS ---
with tabs[4]:
    on = st.checkbox("Activar MAXIMO SKUS", value=params["RULE_TOGGLES"]["MAX_SKUS"], key="t_sku")
    params["RULE_TOGGLES"]["MAX_SKUS"] = on
    val = st.number_input("Máximo de SKUs (LNK) distintos por lote", value=int(params["MAX_SKU"]), min_value=1, step=1)
    params["MAX_SKU"] = val if on else 9999

# --- COMBINACION_PRIORIDAD ---
with tabs[5]:
    st.markdown("Matriz de bloques que pueden mezclarse en un mismo lote (PAST DUE+DUE=VENCIDOS, AHEAD, AHEAD2, OTROS):")
    on = st.checkbox("Activar COMBINACION_PRIORIDAD", value=params["RULE_TOGGLES"]["COMBINACION_PRIORIDAD"], key="t_combo")
    params["RULE_TOGGLES"]["COMBINACION_PRIORIDAD"] = on
    blocks = ["VENCIDOS", "AHEAD", "AHEAD2", "OTROS"]
    default_pairs = set(params["ALLOWED_PAIRS"])
    selected_pairs = []
    st.caption("Marca los pares que se pueden mezclar (la diagonal, mismo bloque, siempre se permite).")
    cols = st.columns(len(blocks))
    pair_state = {}
    for i, b1 in enumerate(blocks):
        for j, b2 in enumerate(blocks):
            if j < i:
                continue
            key = f"pair_{b1}_{b2}"
            default_checked = (b1, b2) in default_pairs or (b2, b1) in default_pairs or b1 == b2
            checked = st.checkbox(f"{b1} ↔ {b2}", value=default_checked, key=key)
            if checked:
                selected_pairs.append((b1, b2))
    if on:
        params["ALLOWED_PAIRS"] = selected_pairs
        params["MIX_ALLOWED"] = set(selected_pairs) | {(b, a) for a, b in selected_pairs}
    else:
        all_pairs = [(a, b) for a in blocks for b in blocks]
        params["MIX_ALLOWED"] = set(all_pairs)

# --- SPLIT_MINIMO ---
with tabs[6]:
    on = st.checkbox("Activar SPLIT_MINIMO", value=params["RULE_TOGGLES"]["SPLIT_MINIMO"], key="t_split")
    params["RULE_TOGGLES"]["SPLIT_MINIMO"] = on
    val = st.number_input("Split mínimo (lbs) — evita splits más pequeños", value=float(params["SPLIT_MIN_LBS_DEFAULT"]), step=50.0)
    params["SPLIT_MIN_LBS_DEFAULT"] = val if on else 0.0
    params["SPLIT_MIN_LBS_ANCHO18"] = st.number_input("Split mínimo para regla ANCHO18 (lbs)", value=float(params["SPLIT_MIN_LBS_ANCHO18"]), step=50.0)

# --- MIX-BLEACH-DYE ---
with tabs[7]:
    st.markdown("BLEACH solo tiene categorías F-2200 y G-1100. Por defecto, en BLEACH NO aplican RESTRICCION_FAMILIA ni RESTRICCION_COLOR.")
    on = st.checkbox("¿Aplicar RESTRICCION_FAMILIA / RESTRICCION_COLOR también en BLEACH?", value=bool(params["APPLY_RULES_BLEACH"]), key="t_bleach")
    params["RULE_TOGGLES"]["MIX_BLEACH_DYE"] = True
    params["APPLY_RULES_BLEACH"] = 1 if on else 0

# --- TIPO_TEJIDO ---
with tabs[8]:
    st.markdown("En categorías grandes (A-4000, B-3300) preferir tejido FLEECE en el scoring, EXCEPTO si la familia tiene RESTRICCION_FAMILIA activa.")
    on = st.checkbox("Activar preferencia TIPO_TEJIDO (FLEECE)", value=params["RULE_TOGGLES"]["TIPO_TEJIDO"], key="t_tejido")
    params["RULE_TOGGLES"]["TIPO_TEJIDO"] = on
    params["TIPO_TEJIDO_ENABLE"] = 1 if on else 0
    params["W_TIPO_TEJIDO_FLEECE"] = st.number_input("Peso del bono FLEECE en el score del lote (W_TIPO_TEJIDO_FLEECE)", value=float(params["W_TIPO_TEJIDO_FLEECE"]), step=0.5)
    cats_sel = st.multiselect("Categorías donde aplica la preferencia FLEECE", options=list(params["MAX_WIDTHS_BY_CAT"].keys()), default=params["TIPO_TEJIDO_CATEGORIAS"])
    params["TIPO_TEJIDO_CATEGORIAS"] = cats_sel
    if st.session_state["df_data"] is not None and "TIPO_TEJIDO" not in st.session_state["df_data"].columns:
        st.warning("⚠️ No se encontró la columna TIPO_TEJIDO en DATA. Esta regla no tendrá efecto hasta que la columna exista.")

# --- %CARGA ---
with tabs[9]:
    st.markdown("Columna por fila en DATA con el % de carga (decimal, ej. 0.7, 0.8, 1.0). Reduce el MAXIMO efectivo de capacidad de la categoría para ese lote sin cambiar la categoría asignada.")
    on = st.checkbox("Activar %CARGA", value=params["RULE_TOGGLES"]["PCT_CARGA"], key="t_carga")
    params["RULE_TOGGLES"]["PCT_CARGA"] = on
    if not on and st.session_state["df_data"] is not None:
        st.session_state["df_data"]["PCT_CARGA"] = 1.0
    if st.session_state["df_data"] is not None and "PCT_CARGA" in st.session_state["df_data"].columns:
        st.caption("Distribución de % de carga encontrada en DATA:")
        st.dataframe(st.session_state["df_data"]["PCT_CARGA"].value_counts().rename("conteo"), use_container_width=True)

# --- ORDEN_REGLAS ---
with tabs[10]:
    st.markdown("Orden de aplicación de las reglas (ANCHO18 > COMBO_ANCHOS > COLOR_R > FAMILIA > DEFAULT). Selecciona un escenario; puedes correr varios y comparar.")
    options = rule_order_options()
    current = params.get("RULE_ORDER", options[0])
    if current not in options:
        options = [current] + options
    idx = options.index(current) if current in options else 0
    chosen = st.selectbox("Orden de reglas (escenario)", options=options, index=idx)
    params["RULE_ORDER"] = chosen
    st.caption("Tip: guarda distintos perfiles (JSON) con cada orden para comparar escenarios y luego ejecutar el loteo varias veces.")

# --- CAPACIDAD TINTORERIA ---
with tabs[11]:
    st.markdown("Tabla editable de capacidades por categoría de tintorería (equivalente a la hoja CAPACIDADES_TINTO original).")
    df_cap_edit = st.data_editor(df_cap, num_rows="dynamic", use_container_width=True, key="ed_cap")
    st.session_state["df_cap"] = df_cap_edit

# --- Avanzado ---
with tabs[12]:
    st.markdown("Parámetros avanzados del motor original (no presentes en REGLAS_OPERATIVAS, mantienen los defaults del script).")
    c1, c2, c3 = st.columns(3)
    with c1:
        params["BEAM_WIDTH"] = st.number_input("BEAM_WIDTH", value=int(params["BEAM_WIDTH"]), min_value=1, step=1)
        params["W_FILL"] = st.number_input("W_FILL", value=float(params["W_FILL"]), step=0.5)
        params["W_CAP_LOSS"] = st.number_input("W_CAP_LOSS", value=float(params["W_CAP_LOSS"]), step=0.5)
    with c2:
        params["W_WIDTH_PREF"] = st.number_input("W_WIDTH_PREF", value=float(params["W_WIDTH_PREF"]), step=0.5)
        params["W_1100_WIDTHS_STRICT"] = st.number_input("W_1100_WIDTHS_STRICT", value=float(params["W_1100_WIDTHS_STRICT"]), step=0.5)
        params["UPGRADE_CATEGORIA"] = 1 if st.checkbox("UPGRADE_CATEGORIA", value=bool(params["UPGRADE_CATEGORIA"])) else 0
    with c3:
        params["TRY_ALL_PRIORITIES"] = 1 if st.checkbox("TRY_ALL_PRIORITIES", value=bool(params["TRY_ALL_PRIORITIES"])) else 0
        params["REQUIRE_WIDTHS_STRICT"] = 1 if st.checkbox("REQUIRE_WIDTHS_STRICT", value=bool(params["REQUIRE_WIDTHS_STRICT"])) else 0
        params["WIDTHS_TARGET_ORDER"] = st.text_input("WIDTHS_TARGET_ORDER", value=params["WIDTHS_TARGET_ORDER"])

    wpl = st.text_input("WIDTH_PREF_LIST (coma-separado)", value=",".join(str(x) for x in params["WIDTH_PREF_LIST"]))
    try:
        params["WIDTH_PREF_LIST"] = [int(x.strip()) for x in wpl.split(",") if x.strip()]
    except Exception:
        pass

    st.markdown("**Filtro de categorías grandes para objetivo de 3/4 anchos (por MIX):**")
    c1, c2 = st.columns(2)
    with c1:
        dye3 = st.text_input("ALLOWED_MAXIMO_FOR_3_WIDTHS_DYE", value=",".join(str(int(x)) for x in params["ALLOWED_MAXIMO_FOR_3_WIDTHS"]["DYE"]))
        dye4 = st.text_input("ALLOWED_MAXIMO_FOR_4_WIDTHS_DYE", value=",".join(str(int(x)) for x in params["ALLOWED_MAXIMO_FOR_4_WIDTHS"]["DYE"]))
    with c2:
        bl3 = st.text_input("ALLOWED_MAXIMO_FOR_3_WIDTHS_BLEACH", value=",".join(str(int(x)) for x in params["ALLOWED_MAXIMO_FOR_3_WIDTHS"]["BLEACH"]))
        bl4 = st.text_input("ALLOWED_MAXIMO_FOR_4_WIDTHS_BLEACH", value=",".join(str(int(x)) for x in params["ALLOWED_MAXIMO_FOR_4_WIDTHS"]["BLEACH"]))

    def _parse_set(s):
        out = set()
        for x in s.split(","):
            x = x.strip()
            if x:
                try:
                    out.add(float(x))
                except Exception:
                    pass
        return out

    params["ALLOWED_MAXIMO_FOR_3_WIDTHS"] = {"DYE": _parse_set(dye3), "BLEACH": _parse_set(bl3)}
    params["ALLOWED_MAXIMO_FOR_4_WIDTHS"] = {"DYE": _parse_set(dye4), "BLEACH": _parse_set(bl4)}

st.session_state["params"] = params

# ---------------------------- 3. Ejecución ----------------------------
st.header("3. Ejecutar Loteo")
if st.button("▶️ Ejecutar Loteo", type="primary"):
    if st.session_state["df_data"] is None:
        st.error("Primero carga un archivo válido.")
    else:
        try:
            df_cap_final = build_cap_dataframe(st.session_state["df_cap"].to_dict("records"))
            progress_bar = st.progress(0.0, text="Iniciando...")

            def cb(frac, msg):
                progress_bar.progress(min(1.0, frac), text=msg)

            with st.spinner("Ejecutando algoritmo de loteo..."):
                df_detalle, df_resumen, df_exced, df_param_out = run_loteo(
                    st.session_state["df_data"], df_cap_final, params, progress_cb=cb
                )
                reports = build_reports(st.session_state["df_data"], df_cap_final, df_detalle, df_resumen)

            st.session_state["resultado"] = {
                "df_detalle": df_detalle, "df_resumen": df_resumen, "df_exced": df_exced,
                "df_param_out": df_param_out, "reports": reports, "df_cap_final": df_cap_final
            }
            st.success(f"✅ Loteo completado: {len(df_resumen)} lotes creados.")
        except Exception as e:
            st.error(f"❌ Error durante la ejecución del loteo: {e}")

# ---------------------------- 4 & 5. Resultados y gráficos ----------------------------
if st.session_state["resultado"] is not None:
    res = st.session_state["resultado"]
    df_detalle = res["df_detalle"]
    df_resumen = res["df_resumen"]
    df_exced = res["df_exced"]
    reports = res["reports"]

    st.header("4. KPIs")
    total_data = float(st.session_state["df_data"]["TOTAL"].sum())
    total_asignado = float(df_detalle["LBS_ASIGNADAS"].sum()) if len(df_detalle) else 0.0
    pct_asignado = (total_asignado / total_data * 100) if total_data > 0 else 0.0
    n_lotes = len(df_resumen)
    skus_sin_asignar = df_exced["LNK"].nunique() if len(df_exced) else 0
    lbs_excedentes = float(df_exced["LBS_RESTANTES"].sum()) if len(df_exced) else 0.0
    fill_avg = float(reports["CAPACIDAD_X_CATEG"]["FILL_RATE"].mean()) * 100 if len(reports["CAPACIDAD_X_CATEG"]) else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("% lbs asignadas", f"{pct_asignado:.1f}%")
    k2.metric("# Lotes creados", f"{n_lotes}")
    k3.metric("# SKUs sin asignar", f"{skus_sin_asignar}")
    k4.metric("Lbs en excedentes", f"{lbs_excedentes:,.0f}")
    k5.metric("Fill rate promedio", f"{fill_avg:.1f}%")

    st.header("5. Reportes")
    report_tabs = st.tabs([
        "DETALLE_LOTES", "RESUMEN_LOTES", "EXCEDENTES", "PARAMETROS",
        "CAPACIDAD_X_CATEG", "PRIORIDAD_VS_ASIG", "LNK_COMPLETITUD",
        "REGLA_STYLE_ANCHO18", "REGLA_COMBINACION_ANCHOS", "REGLA_COLOR_R",
        "REGLA_FAMILIA", "REPORTE_REGLAS_MIX", "OVERSHOOT_SUMMARY", "DECISION_LOG"
    ])
    all_reports = {
        "DETALLE_LOTES": df_detalle, "RESUMEN_LOTES": df_resumen, "EXCEDENTES": df_exced,
        "PARAMETROS": res["df_param_out"],
        **reports
    }
    for tab, (name, df) in zip(report_tabs, all_reports.items()):
        with tab:
            st.dataframe(df, use_container_width=True)
            st.download_button(f"⬇️ Descargar {name}.csv", data=df.to_csv(index=False).encode("utf-8"),
                                file_name=f"{name}.csv", mime="text/csv", key=f"dl_{name}")

    st.header("6. Gráficos")

    if len(reports["CAPACIDAD_X_CATEG"]) > 0:
        df_c = reports["CAPACIDAD_X_CATEG"]
        fig = go.Figure()
        fig.add_bar(x=df_c["CATEGORIA"] + " (" + df_c["MIX"] + ")", y=df_c["CAPACIDAD"], name="Capacidad")
        fig.add_bar(x=df_c["CATEGORIA"] + " (" + df_c["MIX"] + ")", y=df_c["LBS_ASIGNADAS"], name="Asignado")
        fig.add_trace(go.Scatter(x=df_c["CATEGORIA"] + " (" + df_c["MIX"] + ")", y=df_c["FILL_RATE"] * 100,
                                  name="% Llenado", yaxis="y2", mode="lines+markers"))
        fig.update_layout(barmode="group", title="Capacidad vs. Asignado por categoría",
                           yaxis2=dict(overlaying="y", side="right", title="% Llenado"))
        st.plotly_chart(fig, use_container_width=True)

    if len(reports["PRIORIDAD_VS_ASIG"]) > 0:
        df_p = reports["PRIORIDAD_VS_ASIG"]
        fig2 = px.bar(df_p, x="BLOQUE", y=["LBS_ASIGNADAS", "LBS_SIN_ASIGNAR"], facet_col="MIX", barmode="stack",
                      title="Prioridad/bloque: lbs asignadas vs. sin asignar")
        st.plotly_chart(fig2, use_container_width=True)

    if len(df_resumen) > 0:
        fig3 = px.histogram(df_resumen, x="ANCHOS_UNICOS", title="Distribución de # de anchos por lote")
        st.plotly_chart(fig3, use_container_width=True)

    if len(reports["LNK_COMPLETITUD"]) > 0:
        fig4 = px.pie(reports["LNK_COMPLETITUD"], names="ESTADO", title="Estado de completitud por LNK")
        st.plotly_chart(fig4, use_container_width=True)

    if len(df_resumen) > 0:
        fig5 = px.bar(df_resumen["REGLA_DOMINANTE"].value_counts().reset_index(),
                      x="REGLA_DOMINANTE", y="count", title="Top reglas aplicadas (conteo de lotes)")
        st.plotly_chart(fig5, use_container_width=True)

    if len(df_exced) > 0:
        fig6 = px.bar(df_exced.groupby(["MIX"], as_index=False)["LBS_RESTANTES"].sum(),
                      x="MIX", y="LBS_RESTANTES", title="Excedentes por MIX")
        st.plotly_chart(fig6, use_container_width=True)

    st.header("7. Descarga del Excel completo")
    if "excel_bytes" not in st.session_state:
        st.session_state["excel_bytes"] = None

    if st.button("📦 Generar Excel completo"):
        try:
            out_path = "/tmp/RESULTADOS_LOTES.xlsx"
            with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
                used_names = set()
                for name, df in all_reports.items():
                    sheet_name = name[:31]
                    # evitar nombres de hoja duplicados tras el truncado a 31 caracteres
                    base = sheet_name
                    i = 1
                    while sheet_name in used_names:
                        suffix = f"_{i}"
                        sheet_name = base[:31 - len(suffix)] + suffix
                        i += 1
                    used_names.add(sheet_name)
                    df_safe = df.copy()
                    # openpyxl no acepta tz-aware datetimes ni objetos no serializables; forzamos a str si hace falta
                    for col in df_safe.columns:
                        if df_safe[col].dtype == object:
                            df_safe[col] = df_safe[col].apply(lambda v: v if (v is None or isinstance(v, (str, int, float, bool))) else str(v))
                    df_safe.to_excel(writer, index=False, sheet_name=sheet_name)
            format_workbook(out_path, font_name="Cambria", font_size=8)
            with open(out_path, "rb") as f:
                st.session_state["excel_bytes"] = f.read()
            st.success("✅ Excel generado. Usa el botón de abajo para descargarlo.")
        except Exception as e:
            st.session_state["excel_bytes"] = None
            st.error(f"❌ Error generando el Excel: {e}")

    if st.session_state["excel_bytes"] is not None:
        st.download_button(
            "⬇️ Descargar RESULTADOS_LOTES.xlsx",
            data=st.session_state["excel_bytes"],
            file_name="RESULTADOS_LOTES.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_excel_final",
        )
