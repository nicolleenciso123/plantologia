import streamlit as st
import sqlite3
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Plantas Bogotá",
    page_icon="🌱",
    layout="centered"
)

# --- CLAVE API Y CONFIGURACIÓN PL@NTNET ---
PLANTNET_API_KEY = "2b102MvS2gH07X87rRk7w79sO"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}"

# --- FUNCIÓN DE CONEXIÓN A BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect('plantas_bogota.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- TÍTULO PRINCIPAL ---
st.title("🌱 Plantas Bogotá")
st.subheader("Adaptado para la Sabana de Bogotá")
st.write(
    "Identifica especies vegetales mediante fotografía o texto, consulta sus cuidados locales "
    "y agrega nuevas plantas si no están registradas."
)

# --- SELECCIÓN DE MÉTODO DE BÚSQUEDA ---
opcion = st.radio(
    "Selecciona el método de consulta:",
    ("📸 Identificar por Fotografía", "🔍 Búsqueda Manual por Texto")
)

st.divider()

# ==========================================
# OPCIÓN 1: IDENTIFICACIÓN POR FOTOGRAFÍA
# ==========================================
if opcion == "📸 Identificar por Fotografía":
    st.info("💡 En tu celular, esto te permitirá usar la cámara directamente o elegir una foto de tu galería.")
    
    archivo_imagen = st.file_uploader("Sube una imagen de la planta:", type=["jpg", "jpeg", "png"])
    
    if archivo_imagen is not None:
        st.image(archivo_imagen, caption="Imagen cargada", use_container_width=True)
        
        if st.button("🔍 Identificar Planta"):
            with st.spinner("Analizando imagen con Pl@ntNet..."):
                try:
                    # Enviar imagen a la API de Pl@ntNet
                    files = {'images': (archivo_imagen.name, archivo_imagen.getvalue(), archivo_imagen.type)}
                    data = {'organs': 'auto'}  # Configurado en 'auto' para detectar hojas, flores o tallos
                    
                    response = requests.post(PLANTNET_URL, files=files, data=data)
                    
                    if response.status_code == 200:
                        resultado = response.json()
                        mejores_resultados = resultado.get('results', [])
                        
                        if mejores_resultados:
                            top_match = mejores_resultados[0]
                            especie = top_match['species']['scientificNameWithoutAuthor']
                            puntuacion = round(top_match['score'] * 100, 2)
                            
                            st.success(f"**Resultado:** {especie} (Coincidencia: {puntuacion}%)")
                            
                            # Buscar en la base de datos local SQLite
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM plantas WHERE nombre_cientifico LIKE ?", (f"%{especie}%",))
                            planta_local = cursor.fetchone()
                            conn.close()
                            
                            if planta_local:
                                st.subheader("📋 Ficha Técnica (Sabana de Bogotá)")
                                st.write(f"**Nombre Común:** {planta_local['nombre_comun']}")
                                st.write(f"**Origen:** {planta_local['origen']}")
                                st.write(f"**Uso / Cuidados:** {planta_local['cuidados']}")
                            else:
                                st.warning("La planta fue identificada, pero aún no está registrada en la base de datos de la Sabana de Bogotá.")
                        else:
                            st.error("No se encontraron coincidencias claras en la imagen.")
                    else:
                        st.error("Error al conectar con el servicio de identificación. Verifica la clave API.")
                except Exception as e:
                    st.error(f"Ocurrió un error durante el procesamiento: {e}")

# ==========================================
# OPCIÓN 2: BÚSQUEDA MANUAL POR TEXTO
# ==========================================
else:
    busqueda = st.text_input("Escribe el nombre común o científico de la planta:")
    
    if busqueda:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM plantas WHERE nombre_comun LIKE ? OR nombre_cientifico LIKE ?"
        cursor.execute(query, (f"%{busqueda}%", f"%{busqueda}%"))
        resultados = cursor.fetchall()
        conn.close()
        
        if resultados:
            st.success(f"Se encontraron {len(resultados)} resultado(s):")
            for r in resultados:
                with st.expander(f"🌿 {r['nombre_comun']} ({r['nombre_cientifico']})"):
                    st.write(f"**Origen:** {r['origen']}")
                    st.write(f"**Cuidados / Descripción:** {r['cuidados']}")
        else:
            st.error("No se encontraron plantas registradas con ese nombre.")