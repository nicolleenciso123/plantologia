import streamlit as st
import sqlite3
import requests
from PIL import Image

# --- CONFIGURACIÓN DE APIS Y ARCHIVOS ---
PLANTNET_KEY = "2b10il2GHDrmNzBng7ZqQojGre"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_KEY}"
DB_FILE = "plantas_bogota.db"

# Configuración de la página web
st.set_page_config(
    page_title="Plantas Bogotá",
    page_icon="🌱",
    layout="centered"
)

st.title("🌱 Sistema de Identificación de Plantas")
st.markdown("### Adaptado para la Sabana de Bogotá")
st.write("Identifica especies vegetales mediante fotografía o texto, consulta sus cuidados locales y agrega nuevas plantas si no están registradas.")

# Función de búsqueda en SQLite
def buscar_planta_en_sqlite(nombre_buscado):
    if not nombre_buscado:
        return None
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Búsqueda por Nombre Científico
        query = "SELECT * FROM plantas WHERE nombre_cientifico LIKE ?"
        cursor.execute(query, (f"%{nombre_buscado}%",))
        resultado = cursor.fetchone()

        # 2. Búsqueda por Género
        if not resultado and " " in nombre_buscado:
            genero = nombre_buscado.split()[0]
            cursor.execute(query, (f"%{genero}%",))
            resultado = cursor.fetchone()

        # 3. Búsqueda por Nombre Común
        if not resultado:
            query_comun = "SELECT * FROM plantas WHERE nombre_comun LIKE ?"
            cursor.execute(query_comun, (f"%{nombre_buscado}%",))
            resultado = cursor.fetchone()

        conn.close()
        return dict(resultado) if resultado else None
    except sqlite3.Error as e:
        st.error(f"Error al consultar la base de datos: {e}")
        return None

# Función para identificar foto con Pl@ntNet
def identificar_foto_plantnet(uploaded_file):
    try:
        bytes_data = uploaded_file.getvalue()
        files = [("images", ("foto.jpg", bytes_data, "image/jpeg"))]
        
        with st.spinner("🚀 Analizando fotografía con Pl@ntNet..."):
            response = requests.post(PLANTNET_URL, files=files)
        
        if response.status_code == 200:
            datos = response.json()
            if "results" in datos and len(datos["results"]) > 0:
                primer_resultado = datos["results"][0]
                nombre_cientifico = primer_resultado["species"]["scientificNameWithoutAuthor"]
                probabilidad = round(primer_resultado["score"] * 100, 2)
                return nombre_cientifico, probabilidad
            else:
                st.warning("No se encontraron resultados claros en Pl@ntNet.")
                return None, None
        else:
            st.error(f"Error en la API de Pl@ntNet (Código {response.status_code})")
            return None, None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None, None

# --- MENÚ DE NAVEGACIÓN EN LA WEB ---
modo = st.radio("Selecciona el método de consulta:", ["📸 Identificar por Fotografía", "✍️ Búsqueda Manual por Texto"])

nombre_planta_detectada = None

if modo == "📸 Identificar por Fotografía":
    st.info("💡 En tu celular, esto te permitirá usar la cámara directamente o elegir una foto de tu galería.")
    archivo_foto = st.file_uploader("Sube una imagen de la planta:", type=["jpg", "jpeg", "png"])
    
    if archivo_foto is not None:
        st.image(archivo_foto, caption="Imagen cargada", use_column_width=True)
        if st.button("🔍 Procesar e Identificar Planta", type="primary"):
            nombre_cientifico, prob = identificar_foto_plantnet(archivo_foto)
            if nombre_cientifico:
                st.success(f"✅ ¡Identificado con éxito! Especie: **{nombre_cientifico}** ({prob}% de certeza)")
                nombre_planta_detectada = nombre_cientifico

else:
    nombre_texto = st.text_input("Escribe el nombre científico o común (ej. Cilantro, Tomate, Lengua de suegra):")
    if st.button("🔍 Buscar en Base de Datos", type="primary"):
        if nombre_texto:
            nombre_planta_detectada = nombre_texto
        else:
            st.warning("Por favor escribe un nombre válido.")

# --- RESULTADOS Y REGISTRO ---
if nombre_planta_detectada:
    st.divider()
    st.subheader(f"Resultados para: {nombre_planta_detectada}")
    planta = buscar_planta_en_sqlite(nombre_planta_detectada)

    if planta:
        st.success("🌿 ¡Ficha técnica encontrada en la base de datos local de Bogotá!")
        st.markdown(f"""
        - 📌 **Nombre Científico:** {planta.get('nombre_cientifico')}
        - 🏷️ **Nombre Común:** {planta.get('nombre_comun')}
        - 📂 **Familia:** {planta.get('familia')}
        - 🏷️ **Categoría:** {planta.get('categoria')}
        - 🏙️ **Uso en Bogotá:** {planta.get('uso_bogota')}
        - ☀️ **Tipo de Luz:** {planta.get('tipo_luz')}
        - 💧 **Frecuencia de Riego:** {planta.get('frecuencia_riego')}
        - 📍 **Ubicación Sugerida:** {planta.get('ubicacion_sugerida')}
        - 🌡️ **Temperatura Ideal:** {planta.get('temperatura_clima')}
        - ⚠️ **Toxicidad:** {planta.get('toxicidad')}
        - 🐛 **Plagas Comunes:** {planta.get('plagas_comunes')}
        - 💊 **Tratamiento Recomendado:** {planta.get('tratamiento_recomendado')}
        """)
    else:
        st.warning(f"⚠️ '{nombre_planta_detectada}' no está registrada en la base de datos local de Bogotá.")
        st.info("¿Deseas registrarla ahora mismo para que quede guardada?")
        
        with st.form("form_registro"):
            st.write("### 📝 Formulario de Registro de Nueva Planta")
            reg_cientifico = st.text_input("Nombre Científico", value=nombre_planta_detectada)
            reg_comun = st.text_input("Nombre Común o Popular")
            reg_familia = st.text_input("Familia Botánica", value="Ej. Asteraceae")
            reg_categoria = st.text_input("Categoría (ej. Ornamental, Aromática)", value="Ornamental")
            reg_uso = st.text_input("Uso en Bogotá", value="Jardinería urbana")
            reg_luz = st.text_input("Tipo de Luz", value="Semisombra")
            reg_riego = st.text_input("Frecuencia de Riego", value="2 veces por semana")
            reg_ubicacion = st.text_input("Ubicación Sugerida", value="Interior")
            reg_temp = st.text_input("Temperatura Ideal / Clima", value="Frío / 15°C")
            reg_toxicidad = st.text_input("Toxicidad", value="No tóxica")
            reg_plagas = st.text_input("Plagas Comunes", value="Pulgón")
            reg_tratamiento = st.text_input("Tratamiento Recomendado", value="Monitorear humedad")
            
            submitted = st.form_submit_button("💾 Guardar Planta en la Base de Datos")
            if submitted:
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO plantas (
                            nombre_cientifico, nombre_comun, familia, categoria, uso_bogota, 
                            tipo_luz, frecuencia_riego, ubicacion_sugerida, temperatura_clima, 
                            toxicidad, plagas_comunes, tratamiento_recomendado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (reg_cientifico, reg_comun, reg_familia, reg_categoria, reg_uso, 
                          reg_luz, reg_riego, reg_ubicacion, reg_temp, reg_toxicidad, reg_plagas, reg_tratamiento))
                    conn.commit()
                    conn.close()
                    st.success("🎉 ¡Planta registrada exitosamente! Vuelve a buscarla para ver su ficha completa.")
                except sqlite3.Error as e:
                    st.error(f"Error al guardar en la base de datos: {e}")