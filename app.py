import streamlit as st
import sqlite3
import requests
import hashlib

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Plantas Bogotá",
    page_icon="🌱",
    layout="centered"
)

# --- CLAVE API Y CONFIGURACIÓN PL@NTNET ---
PLANTNET_API_KEY = "2b102MvS2gH07X87rRk7w79sO"
PLANTNET_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}"

# --- GESTIÓN DE BASE DE DATOS Y TABLAS ---
def init_db():
    conn = sqlite3.connect('plantas_bogota.db')
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Tabla de historial vinculada al usuario
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

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- CONTROL DE SESIÓN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ==========================================
# PANTALLA DE INICIO DE SESIÓN / REGISTRO
# ==========================================
if not st.session_state.logged_in:
    st.title("🌱 Plantas Bogotá - Acceso")
    st.subheader("Inicia sesión o regístrate para guardar tu historial")
    
    tab1, tab2 = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
    
    with tab1:
        st.write("### Iniciar Sesión")
        user_login = st.text_input("Usuario", key="login_user")
        pass_login = st.text_input("Contraseña", type="password", key="login_pass")
        
        if st.button("Entrar"):
            if user_login and pass_login:
                conn = sqlite3.connect('plantas_bogota.db')
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
        
        if st.button("Registrarse"):
            if user_reg and pass_reg:
                try:
                    conn = sqlite3.connect('plantas_bogota.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", 
                                   (user_reg, hash_password(pass_reg)))
                    conn.commit()
                    conn.close()
                    st.success("¡Cuenta creada con éxito! Ahora ve a la pestaña de Iniciar Sesión.")
                except sqlite3.IntegrityError:
                    st.error("Ese nombre de usuario ya existe. Prueba con otro.")
            else:
                st.warning("Por favor completa todos los campos.")

# ==========================================
# APLICACIÓN PRINCIPAL (SI YA INICIÓ SESIÓN)
# ==========================================
else:
    st.sidebar.write(f"👤 Conectado como: **{st.session_state.username}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    st.title("🌱 Plantas Bogotá")
    st.subheader("Adaptado para la Sabana de Bogotá")
    
    menu = st.selectbox(
        "Selecciona una sección:",
        ("🔍 Identificar / Buscar Planta", "📜 Mi Historial de Búsquedas")
    )
    
    st.divider()

    if menu == "🔍 Identificar / Buscar Planta":
        opcion = st.radio(
            "Selecciona el método de consulta:",
            ("📸 Identificar por Fotografía", "🔍 Búsqueda Manual por Texto")
        )
        
        # --- OPCIÓN 1: FOTOGRAFÍA ---
        if opcion == "📸 Identificar por Fotografía":
            st.info("💡 En tu celular, esto te permitirá usar la cámara directamente o elegir una foto de tu galería.")
            archivo_imagen = st.file_uploader("Sube una imagen de la planta:", type=["jpg", "jpeg", "png"])
            
            if archivo_imagen is not None:
                st.image(archivo_imagen, caption="Imagen cargada", use_container_width=True)
                
                if st.button("🔍 Identificar Planta"):
                    with st.spinner("Analizando imagen con Pl@ntNet..."):
                        try:
                            files = {'images': (archivo_imagen.name, archivo_imagen.getvalue(), archivo_imagen.type)}
                            data = {'organs': 'auto'}
                            response = requests.post(PLANTNET_URL, files=files, data=data)
                            
                            if response.status_code == 200:
                                resultado = response.json()
                                mejores_resultados = resultado.get('results', [])
                                
                                if mejores_resultados:
                                    top_match = mejores_resultados[0]
                                    especie = top_match['species']['scientificNameWithoutAuthor']
                                    puntuacion = round(top_match['score'] * 100, 2)
                                    
                                    st.success(f"**Resultado:** {especie} (Coincidencia: {puntuacion}%)")
                                    
                                    conn = sqlite3.connect('plantas_bogota.db')
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT * FROM plantas WHERE nombre_cientifico LIKE ?", (f"%{especie}%",))
                                    planta_local = cursor.fetchone()
                                    
                                    detalle_historial = f"Identificación por foto - Coincidencia: {puntuacion}%"
                                    cursor.execute("INSERT INTO historial (username, nombre_planta, detalle) VALUES (?, ?, ?)",
                                                   (st.session_state.username, especie, detalle_historial))
                                    conn.commit()
                                    conn.close()
                                    
                                    if planta_local:
                                        st.subheader("📋 Ficha Técnica (Sabana de Bogotá)")
                                        st.write(f"**Nombre Común:** {planta_local[1] if len(planta_local)>1 else 'N/D'}")
                                        st.write(f"**Nombre Científico:** {planta_local[2] if len(planta_local)>2 else especie}")
                                        st.write(f"**Origen / Cuidados:** {planta_local[3] if len(planta_local)>3 else 'Información no disponible'}")
                                    else:
                                        st.warning("Identificada, pero pendiente de registro detallado en la Sabana de Bogotá.")
                                else:
                                    st.error("No se encontraron coincidencias claras.")
                            else:
                                st.error("Error al conectar con Pl@ntNet.")
                        except Exception as e:
                            st.error(f"Ocurrió un error: {e}")

        # --- OPCIÓN 2: TEXTO ---
        else:
            busqueda = st.text_input("Escribe el nombre común o científico de la planta:")
            
            if busqueda:
                conn = sqlite3.connect('plantas_bogota.db')
                cursor = conn.cursor()
                query = "SELECT * FROM plantas WHERE nombre_comun LIKE ? OR nombre_cientifico LIKE ?"
                cursor.execute(query, (f"%{busqueda}%", f"%{busqueda}%"))
                resultados = cursor.fetchall()
                
                if resultados:
                    st.success(f"Se encontraron {len(resultados)} resultado(s):")
                    for r in resultados:
                        # Usamos posiciones numéricas seguras de las columnas para evitar errores de nombres
                        nombre_c = r[1] if len(r) > 1 else "Planta"
                        nombre_ci = r[2] if len(r) > 2 else ""
                        info_extra = r[3] if len(r) > 3 else "Sin detalles registrados"
                        
                        with st.expander(f"🌿 {nombre_c} ({nombre_ci})"):
                            st.write(f"**Detalles / Cuidados:** {info_extra}")
                            
                            # Guardar en el historial
                            cursor.execute("INSERT INTO historial (username, nombre_planta, detalle) VALUES (?, ?, ?)",
                                           (st.session_state.username, nombre_c, f"Búsqueda por texto: {nombre_ci}"))
                            conn.commit()
                else:
                    st.error("No se encontraron plantas registradas con ese nombre.")
                conn.close()

    # ==========================================
    # SECCIÓN: MI HISTORIAL
    # ==========================================
    else:
        st.subheader(f"📜 Historial de consultas de: {st.session_state.username}")
        
        conn = sqlite3.connect('plantas_bogota.db')
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