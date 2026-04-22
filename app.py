# Nombre del archivo: app.py
from flask import Flask, request, session
from db import db
from routes import tienda_bp, admin_bp
import os
from flask_socketio import SocketIO, emit, join_room
from sqlalchemy import text 

# Instancia global de SocketIO
socketio = SocketIO()

# Diccionario para rastrear usuarios conectados: {user_id: sid}
usuarios_conectados = {}
usuarios_lobby = {} 

# Estado temporal de la Sala Virtual
estado_lobby = {
    'cola_palabra': [],
    'materiales': [],
    'fijado': None,
    'permiso_materiales': False # Control de permisos para subir archivos
}

def create_app():
    app = Flask(__name__)
    
    # Configuración de la base de datos SQLite
    base_dir = os.path.abspath(os.path.dirname(__name__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'tienda.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Uso de variable de entorno para la SECRET_KEY (con fallback para dev local)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'llave_secreta_glassmorphic_store_123')
    
    # Inicializar la base de datos con la app
    db.init_app(app)
    
    # Registrar los Blueprints
    app.register_blueprint(tienda_bp)
    app.register_blueprint(admin_bp)
    
    # MEJORA SEGURIDAD (Punto 3.D): Configuración de CORS basada en entorno. 
    # En producción deberías definir CORS_ORIGINS="https://tudominio.com"
    origenes_permitidos = os.environ.get('CORS_ORIGINS', '*')
    if origenes_permitidos != '*':
        origenes_permitidos = origenes_permitidos.split(',')
        
    # Inicializar SocketIO (manage_session=False asegura que usemos la sesión nativa de Flask)
    socketio.init_app(app, cors_allowed_origins=origenes_permitidos, manage_session=False)
    
    with app.app_context():
        # Ahora Flask-Migrate se encargará de los cambios de esquema limpiamente.
        db.create_all()

        # ==========================================
        # CREACIÓN AUTOMÁTICA DE SUPERUSUARIOS
        # ==========================================
        from werkzeug.security import generate_password_hash
        from model import Usuario
        
        correos_admin = ['kenth1977@gmail.com', 'lthikingcr@gmail.com']
        pwd_admin = generate_password_hash('CR129x7848n', method='pbkdf2:sha256')
        
        for correo in correos_admin:
            if not Usuario.query.filter_by(email=correo).first():
                admin = Usuario(
                    nombre='Admin',
                    primer_apellido='Sistema',
                    segundo_apellido='',
                    telefono='88888888',
                    email=correo,
                    password=pwd_admin,
                    opciones_extra={'is_admin': True, 'tema': 'tema-default'}
                )
                db.session.add(admin)
        db.session.commit()

    return app

# =======================================================
# --- EVENTOS DE SOCKET.IO PARA EL CHAT AVANZADO ---
# =======================================================
@socketio.on('conectar_usuario')
def handle_conectar(data):
    # SOLUCIÓN DE SEGURIDAD: Confiar en la sesión del servidor, no en el cliente
    user_id = session.get('user_id')
    if user_id:
        user_id_str = str(user_id)
        usuarios_conectados[user_id_str] = request.sid
        join_room(f"user_{user_id_str}")
        emit('estado_usuarios', {'user_id': user_id_str, 'status': 'online'}, broadcast=True)

@socketio.on('pedir_estados')
def handle_pedir_estados():
    emit('lista_estados', list(usuarios_conectados.keys()), room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    for uid, sid in list(usuarios_conectados.items()):
        if sid == request.sid:
            del usuarios_conectados[uid]
            emit('estado_usuarios', {'user_id': uid, 'status': 'offline'}, broadcast=True)
            break
            
    # Remover al usuario de la sala virtual si cierra la página
    if request.sid in usuarios_lobby:
        user_data = usuarios_lobby.pop(request.sid)
        estado_lobby['cola_palabra'] = [u for u in estado_lobby['cola_palabra'] if u['user_id'] != user_data['user_id']]
        emit('participante_salio_lobby', {'user_id': user_data['user_id'], 'nombre': user_data['nombre']}, room='LobbyGlobal')
        emit('actualizar_cola', estado_lobby['cola_palabra'], room='LobbyGlobal')

@socketio.on('enviar_mensaje')
def handle_mensaje(data):
    from model import Mensaje
    from db import db
    
    # SOLUCIÓN SPOOFING: Obtenemos el remitente desde la sesión segura
    remitente_id = session.get('user_id')
    if not remitente_id:
        # MEJORA (Punto 4.1): Loguear el intento silencioso
        print("⚠️ Intento de envío de mensaje rechazado: No hay sesión activa.")
        return 
    
    nuevo_msg = Mensaje(
        remitente_id=remitente_id, # <-- Seguro
        destinatario_id=data.get('destinatario_id'),
        texto=data.get('texto'),
        archivo_url=data.get('archivo_url'),
        tipo_archivo=data.get('tipo_archivo'),
        nombre_archivo=data.get('nombre_archivo')
    )
    db.session.add(nuevo_msg)
    db.session.commit()
    
    msg_dict = nuevo_msg.to_dict()
    
    if data.get('destinatario_id'):
        emit('nuevo_mensaje', msg_dict, room=f"user_{data.get('destinatario_id')}")
        emit('nuevo_mensaje', msg_dict, room=f"user_{remitente_id}")
    else:
        emit('nuevo_mensaje', msg_dict, broadcast=True)

@socketio.on('marcar_leido')
def handle_leido(data):
    from model import Mensaje
    from db import db
    
    user_id = session.get('user_id')
    if not user_id: return
    
    msg_id = data.get('mensaje_id')
    msg = Mensaje.query.get(msg_id)
    # Validamos que el mensaje exista y que el usuario actual sea el destinatario
    if msg and msg.destinatario_id == user_id:
        msg.leido = True
        db.session.commit()
        emit('mensaje_actualizado', {'id': msg_id, 'leido': True}, room=f"user_{msg.remitente_id}")

@socketio.on('borrar_mensaje')
def handle_borrar(data):
    from model import Mensaje, Usuario
    from db import db
    
    # SOLUCIÓN SPOOFING: Tomamos el ID del usuario de la sesión
    user_id = session.get('user_id')
    if not user_id: return
    
    msg_id = data.get('mensaje_id')
    tipo = data.get('tipo') 
    
    msg = Mensaje.query.get(msg_id)
    if msg:
        # Borrar para todos (solo el autor puede)
        if tipo == 'todos' and str(msg.remitente_id) == str(user_id):
            msg.borrado = True
            msg.texto = "🚫 Este mensaje fue eliminado."
            msg.archivo_url = None
            db.session.commit()
            emit('mensaje_borrado', {'id': msg_id}, broadcast=True)
            
        # Borrar para mí (Nueva lógica relacional sin CSV)
        elif tipo == 'mi':
            usuario = Usuario.query.get(user_id)
            if usuario and usuario not in msg.oculto_para_usuarios:
                msg.oculto_para_usuarios.append(usuario)
                db.session.commit()
            emit('mensaje_oculto', {'id': msg_id}, room=f"user_{user_id}")


# =======================================================
# --- EVENTOS DEL LOBBY DE VIDEOLLAMADAS Y MATERIALES ---
# =======================================================

@socketio.on('webrtc_signal')
def handle_webrtc_signal(data):
    """
    CORRECCIÓN CRÍTICA WEBRTC (Punto 3.A):
    En lugar de hacer broadcast a todos (lo cual rompe el Peer-to-Peer y satura la sala),
    ahora enviamos la señal estrictamente al usuario destino (target_id).
    """
    target_id = data.get('target_id')
    if target_id:
        emit('webrtc_signal', data, room=f"user_{target_id}")
    else:
        # Fallback temporal por si el frontend no ha sido actualizado aún
        emit('webrtc_signal', data, broadcast=True, include_self=False)

@socketio.on('unirse_lobby')
def handle_unirse_lobby(data):
    user_id = str(session.get('user_id'))
    nombre = data.get('nombre')
    if user_id:
        join_room('LobbyGlobal')
        usuarios_lobby[request.sid] = {'user_id': user_id, 'nombre': nombre}
        
        # Enviar el estado completo al recién llegado
        emit('lista_participantes_lobby', list(usuarios_lobby.values()), room=request.sid)
        emit('actualizar_cola', estado_lobby['cola_palabra'], room=request.sid)
        emit('actualizar_materiales', estado_lobby['materiales'], room=request.sid)
        
        # Enviar permiso inicial de subida de materiales
        emit('estado_inicial_lobby', {'permiso_materiales': estado_lobby['permiso_materiales']}, room=request.sid)
        
        if estado_lobby['fijado']:
            emit('actualizar_escenario', estado_lobby['fijado'], room=request.sid)
            
        emit('nuevo_participante_lobby', {'user_id': user_id, 'nombre': nombre}, room='LobbyGlobal', include_self=False)

@socketio.on('transmitir_mp4')
def handle_transmitir_mp4(data):
    emit('recibir_mp4', data, room='LobbyGlobal', include_self=False)

@socketio.on('cerrar_sala_global')
def handle_cerrar_sala():
    if session.get('is_admin'):
        emit('sala_cerrada', room='LobbyGlobal')

@socketio.on('expulsar_usuario')
def handle_expulsar(data):
    if session.get('is_admin'):
        emit('usuario_expulsado', {'user_id': data.get('user_id')}, room='LobbyGlobal')

@socketio.on('admin_accion_masiva')
def handle_accion_masiva(data):
    if session.get('is_admin'):
        emit('fuerza_accion', {'accion': data.get('accion')}, room='LobbyGlobal', include_self=False)

@socketio.on('admin_accion_individual')
def handle_accion_individual(data):
    if session.get('is_admin'):
        emit('fuerza_accion', {'accion': data.get('accion')}, room=f"user_{data.get('target_id')}")

# --- Petición de Turnos (Levantar Mano) ---
@socketio.on('pedir_palabra')
def handle_pedir_palabra(data):
    user_id = str(session.get('user_id'))
    nombre = data.get('nombre')
    if not any(u['user_id'] == user_id for u in estado_lobby['cola_palabra']):
        estado_lobby['cola_palabra'].append({'user_id': user_id, 'nombre': nombre})
    emit('actualizar_cola', estado_lobby['cola_palabra'], room='LobbyGlobal')

@socketio.on('bajar_mano')
def handle_bajar_mano(data):
    user_id = str(data.get('user_id')) 
    estado_lobby['cola_palabra'] = [u for u in estado_lobby['cola_palabra'] if u['user_id'] != user_id]
    emit('actualizar_cola', estado_lobby['cola_palabra'], room='LobbyGlobal')

# --- Control de Escenario (PiP) ---
@socketio.on('fijar_escenario')
def handle_fijar(data):
    if session.get('is_admin'):
        estado_lobby['fijado'] = data
        emit('actualizar_escenario', data, room='LobbyGlobal')

# --- Gestión de Materiales ---
@socketio.on('toggle_permiso_materiales')
def handle_toggle_materiales(data):
    if session.get('is_admin'):
        estado_lobby['permiso_materiales'] = data.get('permitir')
        emit('actualizar_permiso_materiales', {'permitir': estado_lobby['permiso_materiales']}, room='LobbyGlobal')

@socketio.on('compartir_material')
def handle_material(data):
    # Verificamos que el usuario tenga permiso para subir (sea admin o permiso activo)
    if session.get('is_admin') or estado_lobby['permiso_materiales']:
        import uuid
        data['id'] = str(uuid.uuid4())
        estado_lobby['materiales'].append(data)
        emit('actualizar_materiales', estado_lobby['materiales'], room='LobbyGlobal')

@socketio.on('borrar_material')
def handle_borrar_material(data):
    if session.get('is_admin'):
        mat_id = data.get('id')
        estado_lobby['materiales'] = [m for m in estado_lobby['materiales'] if m.get('id') != mat_id]
        emit('actualizar_materiales', estado_lobby['materiales'], room='LobbyGlobal')

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)