import streamlit as st
import sqlite3
import requests
import hashlib
from PIL import Image

# --- CONFIGURACIÓN DE APIS Y ARCHIVOS ---
PLANTNET_KEY = "2b10il2GHDrmNzBng7ZqQojGre"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_KEY}"

# Base de datos 1: Catálogo de Plantas (Intacta y Segura)
DB_PLANTAS = "plantas_bogota.db"

# Base de datos 2: Nueva base exclusiva para Usuarios e Historial
DB_USUARIOS = "usuarios_historial.db"

# --- INICIALIZAR LA BASE DE DATOS DE USUARIOS ---
def init_user_db():
    try:
        conn = sqlite3.connect(DB_USUARIOS)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                nombre_planta TEXT NOT NULL,
                detalle TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Error creando base de datos de usuarios: {e}")

init_user_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Control de Sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# Configuración de la página web
st.set_page_config(
    page_title="Plantas Bogotá",
    page_icon="🌱",
    layout="centered"
)

# ==========================================
# PANTALLA DE INICIO DE SESIÓN / REGISTRO
# ==========================================
if not st.session_state.logged_in:
    st.title("🌱 Plantas Bogotá - Acceso")
    st.markdown("### Inicia sesión o regístrate para guardar tu historial personal")
    
    tab1, tab2 = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        st.write("### Iniciar Sesión")
        user_login = st.text_input("Usuario", key="login_user")
        pass_login = st.text_input("Contraseña", type="password", key="login_pass")
        
        if st.button("Entrar", type="primary"):
            if user_login and pass_login:
                conn = sqlite3.connect(DB_USUARIOS)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", 
                               (user_login, hash_password(pass_login)))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user_login
                    st.success(f"¡Bienvenido de nuevo, {user_login}!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
            else:
                st.warning("Por favor completa todos los campos.")
                
    with tab2:
        st.write("### Crear Cuenta Nueva")
        user_reg = st.text_input("Nuevo Usuario", key="reg_user")
        pass_reg = st.text_input("Nueva Contraseña", type="password", key="reg_pass")
        
        if st.button("Registrarse", type="primary"):
            if user_reg and pass_reg:
                try:
                    conn = sqlite3.connect(DB_USUARIOS)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", 
                                   (user_reg, hash_password(pass_reg)))
                    conn.commit()
                    conn.close()
                    st.success("¡Cuenta creada con éxito! Ve a la pestaña de Iniciar Sesión.")
                except sqlite3.IntegrityError:
                    st.error("Ese nombre de usuario ya existe. Prueba con otro.")
            else:
                st.warning("Por favor completa todos los campos.")

# ==========================================
# APLICACIÓN PRINCIPAL (SI YA INICIÓ SESIÓN)
# ==========================================
else:
    # Barra lateral con sesión activa
    st.sidebar.write(f"👤 Conectado: **{st.session_state.username}**")
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    st.title("🌱 Sistema de Identificación de Plantas")
    st.markdown("### Adaptado para la Sabana de Bogotá")
    st.write("Identifica especies vegetales mediante fotografía o texto, consulta sus cuidados locales y agrega nuevas plantas si no están registradas.")

    # Función de búsqueda en SQLite (Base de datos 1: Plantas)
    def buscar_planta_en_sqlite(nombre_buscado):
        if not nombre_buscado:
            return None
        try:
            conn = sqlite3.connect(DB_PLANTAS)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM plantas WHERE nombre_cientifico LIKE ?"
            cursor.execute(query, (f"%{nombre_buscado}%",))
            resultado = cursor.fetchone()

            if not resultado and " " in nombre_buscado:
                genero = nombre_buscado.split()[0]
                cursor.execute(query, (f"%{genero}%",))
                resultado = cursor.fetchone()

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

    # Función para guardar en el historial (Base de datos 2)
    def guardar_historial(nombre_planta, detalle):
        try:
            conn = sqlite3.connect(DB_USUARIOS)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO historial (username, nombre_planta, detalle) VALUES (?, ?, ?)",
                           (st.session_state.username, nombre_planta, detalle))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Error al guardar historial: {e}")

    # --- MENÚ DE NAVEGACIÓN EN LA WEB ---
    menu_opciones = ["🔍 Buscar / Identificar Planta", "📜 Mi Historial de Consultas"]
    modo_seleccion = st.selectbox("Selecciona una sección:", menu_opciones)

    if modo_seleccion == "🔍 Buscar / Identificar Planta":
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
                        guardar_historial(nombre_cientifico, f"Identificación por foto - Certeza: {prob}%")

        else:
            nombre_texto = st.text_input("Escribe el nombre científico o común (ej. Cilantro, Tomate, Lengua de suegra):")
            if st.button("🔍 Buscar en Base de Datos", type="primary"):
                if nombre_texto:
                    nombre_planta_detectada = nombre_texto
                    guardar_historial(nombre_texto, "Búsqueda manual por texto")
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
                            conn = sqlite3.connect(DB_PLANTAS)
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

    # ==========================================
    # SECCIÓN: MI HISTORIAL
    # ==========================================
    else:
        st.subheader(f"📜 Historial de consultas de: {st.session_state.username}")
        
        conn = sqlite3.connect(DB_USUARIOS)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre_planta, detalle, fecha FROM historial WHERE username = ? ORDER BY id DESC", (st.session_state.username,))
        historial_usuario = cursor.fetchall()
        conn.close()
        
        if historial_usuario:
            st.write("Aquí puedes ver todas las plantas que has consultado o identificado:")
            for item in historial_usuario:
                with st.container():
                    st.markdown(f"🌿 **{item[0]}**")
                    st.caption(f"Detalle: {item[1]} | Fecha: {item[2]}")
                    st.divider()
        else:
            st.info("Aún no tienes registros en tu historial. ¡Empieza a buscar o identificar plantas!")