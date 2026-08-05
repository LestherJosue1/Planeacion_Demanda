import re

def _first_number_in_text(text, default=None):
    """
    Extrae el primer número válido de un texto de manera robusta, 
    evitando capturar índices o valores numéricos erróneos en descripciones complejas.
    """
    if not text or pd.isna(text):
        return default
    
    # Buscar patrones numéricos con o sin decimales
    m = re.findall(r"(\d+(?:\.\d+)?)", str(text))
    if m:
        try:
            return float(m[0])
        except ValueError:
            return default
            
    return default


def parse_reglas_operativas(df_reglas):
    """
    Parsea las reglas operativas desde el archivo de configuración o Excel.
    """
    parsed_rules = {}
    
    for idx, row in df_reglas.iterrows():
        # Lógica de parseo estructurada de reglas
        clave = str(row.get("PARAMETRO", "")).strip().upper()
        valor_raw = row.get("VALOR", None)
        
        if not clave:
            continue
            
        parsed_rules[clave] = valor_raw
        
    return parsed_rules
