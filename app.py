import sqlite3

def buscar_planta_inteligente(nombre_buscado):
    """
    Busca una planta primero en la base de datos principal (plantas_bogota.db).
    Si no la encuentra, recurre a la base de datos secundaria (plantas_bogota2.db).
    """
    nombre_limpio = '%' + nombre_buscado.strip() + '%'
    
    # --- PASO 1: Buscar en la base de datos principal ---
    try:
        conexion_ppal = sqlite3.connect("plantas_bogota.db")
        cursor_ppal = conexion_ppal.cursor()
        
        # Ajusta 'plantas' y 'nombre' si tus nombres de tabla/columna son diferentes
        cursor_ppal.execute("SELECT * FROM plantas WHERE nombre LIKE ?", (nombre_limpio,))
        resultado = cursor_ppal.fetchone()
        conexion_ppal.close()
        
        if resultado:
            return resultado, "🌿 Encontrado en el catálogo principal de Plantas Bogotá."
            
    except Exception as e:
        print(f"Error en base principal: {e}")

    # --- PASO 2: Si NO está en la principal, buscar en la secundaria ---
    try:
        conexion_sec = sqlite3.connect("plantas_bogota2.db")
        cursor_sec = conexion_sec.cursor()
        
        # Ajusta 'plantas' y 'nombre' si en la segunda base se llaman distinto
        cursor_sec.execute("SELECT * FROM plantas WHERE nombre LIKE ?", (nombre_limpio,))
        resultado_secundario = cursor_sec.fetchone()
        conexion_sec.close()
        
        if resultado_secundario:
            return resultado_secundario, "🔍 Encontrado en la base de datos de respaldo (Plantas Bogotá 2)."
            
    except Exception as e:
        print(f"Error en base secundaria: {e}")

    # Si no aparece en ninguna de las dos
    return None, "❌ La planta no se encuentra registrada en ninguna base de datos."