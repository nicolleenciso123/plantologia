import streamlit as st
import sqlite3
import hashlib

# ==========================================
# 1. INICIALIZACIÓN DE BASES DE DATOS
# ==========================================
def init_user_db():
    """Crea la base de datos de usuarios e historial si no existen."""
    conexion = sqlite3.connect("usuarios_historial.db")
    cursor = conexion.cursor()
    
    # Tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # Tabla de historial
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            nombre_planta TEXT NOT NULL,
            detalle TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conexion.commit()
    conexion.close()

# Ejecutamos la creación de la base de datos de usuarios al iniciar
init_user_db()

# Función para encriptar contraseñas con SHA-256
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# ==========================================
# 2. FUNCIÓN DE BÚSQUEDA INTELIGENTE (DOBLE BASE)
# ==========================================
def buscar_planta_inteligente(nombre_buscado):
    """
    Busca una planta primero en plantas_bogota.db.
    Si no la encuentra, recurre a plantas_bogota2.db.
    """
    nombre_limpio = '%' + nombre_buscado.strip() + '%'
    
    # --- PASO 1: Buscar en la base de datos principal ---
    try:
        conexion_ppal = sqlite3.connect("plantas_bogota.db")
        cursor_ppal = conexion_ppal.cursor()
        
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
        
        cursor_sec.execute("SELECT * FROM plantas WHERE nombre LIKE ?", (nombre_limpio,))
        resultado_secundario = cursor_sec.fetchone()
        conexion_sec.close()
        
        if resultado_secundario:
            return resultado_secundario, "🔍 Encontrado en la base de datos de respaldo (Plantas Bogotá 2)."
            
    except Exception as e:
        print(f"Error en base secundaria: {e}")

    # Si no aparece en ninguna de las dos
    return None, "❌ La planta no se encuentra registrada en ninguna base de datos."

# ==========================================
# 3. INTERFAZ DE USUARIO CON STREAMLIT
# ==========================================
st.title("🌱 Plantas Bogotá - Sistema de Catálogo y Usuarios")

# Menú lateral de navegación
menu = ["Inicio / Buscar", "Registrarse", "Iniciar Sesión", "📜 Mi Historial"]
eleccion = st.sidebar.selectbox("Menú de Navegación", menu)

# Control de sesión en Streamlit
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# --- SECCIÓN: REGISTRARSE ---
if eleccion == "Registrarse":
    st.subheader("📝 Crear una nueva cuenta")
    nuevo_user = st.text_input("Nombre de usuario")
    nuevo_pass = st.text_input("Contraseña", type="password")
    
    if st.button("Registrarse"):
        if nuevo_user and nuevo_pass:
            try:
                conexion = sqlite3.connect("usuarios_historial.db")
                cursor = conexion.cursor()
                cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", 
                               (nuevo_user, hash_password(nuevo_pass)))
                conexion.commit()
                conexion.close()
                st.success("¡Cuenta creada con éxito! Ahora ve a Iniciar Sesión.")
            except sqlite3.IntegrityError:
                st.error("El nombre de usuario ya existe. Prueba con otro.")
        else:
            st.warning("Por favor completa todos los campos.")

# --- SECCIÓN: INICIAR SESIÓN ---
elif eleccion == "Iniciar Sesión":
    st.subheader("🔑 Acceso a tu cuenta")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar"):
        conexion = sqlite3.connect("usuarios_historial.db")
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", 
                       (user, hash_password(password)))
        data = cursor.fetchone()
        conexion.close()
        
        if data:
            st.session_state.logged_in = True
            st.session_state.username = user
            st.success(f"¡Bienvenido de nuevo, {user}!")
        else:
            st.error("Usuario o contraseña incorrectos.")

# --- SECCIÓN: INICIO / BUSCAR PLANTAS ---
elif eleccion == "Inicio / Buscar":
    st.subheader("🔍 Buscador Inteligente de Plantas")
    
    if st.session_state.logged_in:
        st.info(f"Sesión activa como: **{st.session_state.username}**")
    else:
        st.warning("Estás buscando como invitado. Inicia sesión para guardar tu historial.")
        
    busqueda = st.text_input("Escribe el nombre de la planta que deseas consultar:")
    
    if st.button("Buscar Planta"):
        if busqueda:
            resultado, mensaje = buscar_planta_inteligente(busqueda)
            st.write(mensaje)
            
            if resultado:
                st.success("¡Información de la planta encontrada!")
                st.write(resultado) # Aquí puedes mostrar los campos específicos de tu tabla
                
                # Si hay usuario logueado, guardamos la consulta en el historial
                if st.session_state.logged_in:
                    conexion = sqlite3.connect("usuarios_historial.db")
                    cursor = conexion.cursor()
                    cursor.execute("""
                        INSERT INTO historial (username, nombre_planta, detalle)
                        VALUES (?, ?, ?)
                    """, (st.session_state.username, busqueda, mensaje))
                    conexion.commit()
                    conexion.close()
            else:
                st.error("No se hallaron registros.")
        else:
            st.warning("Por favor ingresa un nombre para buscar.")

# --- SECCIÓN: MI HISTORIAL ---
elif eleccion == "📜 Mi Historial":
    st.subheader("📜 Tus consultas recientes")
    
    if st.session_state.logged_in:
        conexion = sqlite3.connect("usuarios_historial.db")
        cursor = conexion.cursor()
        cursor.execute("SELECT nombre_planta, detalle, fecha FROM historial WHERE username = ?", (st.session_state.username,))
        historial_usuario = cursor.fetchall()
        conexion.close()
        
        if historial_usuario:
            for planta, detalle, fecha in historial_usuario:
                st.write(f"- **{fecha}**: Buscaste *{planta}* ({detalle})")
        else:
            st.info("Aún no tienes consultas registradas en tu historial.")
    else:
        st.warning("Debes iniciar sesión para ver tu historial de consultas.")ss