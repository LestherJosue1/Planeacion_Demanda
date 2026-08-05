import pandas as pd
import numpy as np
from itertools import combinations
import json

# --- FUNCIÓN DE SANITIZACIÓN DE TIPOS Y ESTADOS ---
def sanitize_params(params):
    """
    Garantiza que los parámetros importados desde JSON o manipulados en Streamlit 
    mantengan los tipos estrictos que el motor matemático espera (Sets de Tuplas, Floats, etc.).
    """
    if "MIX_ALLOWED" in params:
        if isinstance(params["MIX_ALLOWED"], (list, set)):
            params["MIX_ALLOWED"] = {tuple(p) for p in params["MIX_ALLOWED"]}
            
    if "ALLOWED_PAIRS" in params:
        if isinstance(params["ALLOWED_PAIRS"], (list, set)):
            params["ALLOWED_PAIRS"] = [tuple(p) for p in params["ALLOWED_PAIRS"]]

    # Sanitizar mapas de anchos máximos permitidos por tipo de tinte
    for key_map in ["ALLOWED_MAXIMO_FOR_3_WIDTHS", "ALLOWED_MAXIMO_FOR_4_WIDTHS"]:
        if key_map in params and isinstance(params[key_map], dict):
            sanitized_map = {}
            for dye_type, val_set in params[key_map].items():
                sanitized_map[dye_type] = {float(x) for x in val_set}
            params[key_map] = sanitized_map

    return params


def can_mix_blocks(b1, b2, allowed_pairs):
    """
    Valida si dos bloques pueden mezclarse según las parejas permitidas.
    Soporta tanto sets de tuplas como listas de tuplas por seguridad.
    """
    if b1 == b2:
        return True
    
    # Normalizar a tupla por si viene de JSON degradado
    pair1 = (str(b1), str(b2))
    pair2 = (str(b2), str(b1))
    
    if isinstance(allowed_pairs, set):
        return pair1 in allowed_pairs or pair2 in allowed_pairs
    else:
        # Búsqueda segura en lista de tuplas o listas anidadas
        for p in allowed_pairs:
            p_tuple = (str(p[0]), str(p[1]))
            if p_tuple == pair1 or p_tuple == pair2:
                return True
    return False


def filter_ranges_for_width_target(ranges_try, mixv, width_target, params):
    """
    Filtra los rangos considerando el set de anchos máximos permitidos con tipado robusto.
    """
    if not ranges_try:
        return []
        
    allowed_map = params.get("ALLOWED_MAXIMO_FOR_3_WIDTHS", {})
    allowed = allowed_map.get(mixv, None)
    
    if allowed and len(allowed) > 0:
        # Conversión estricta a float para evitar fallas de igualdad en sets
        return [r for r in ranges_try if float(r.get("MAXIMO", 0)) in {float(x) for x in allowed}]
    
    return ranges_try


def run_loteo(df_input, params):
    """
    Ejecuta el motor principal de loteo aplicando la sanitización de parámetros inicial.
    """
    # 1. Blindar parámetros ante entradas de Streamlit o JSON
    params = sanitize_params(params)
    
    # 2. Lógica del motor (ejemplo de procesamiento base)
    resultados = []
    
    # (Aquí va el resto de tu lógica de procesamiento de lotes existente en el motor...)
    # Asegúrate de usar can_mix_blocks(b1, b2, params["MIX_ALLOWED"]) en tus iteraciones de combinación.
    
    return {
        "status": "success",
        "params_utilizados": params,
        "total_registros": len(df_input) if df_input is not None else 0,
        "resultado_lotes": resultados
    }
