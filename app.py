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

def create_app():
    app = Flask(__name__)
    
    # Configuración de la base de datos SQLite
    base_dir = os.path.abspath(os.path.dirname(__name__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'tienda.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # MEJORA: Uso de variable de entorno para la SECRET_KEY (con fallback para dev local)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'llave_secreta_glassmorphic_store_123')
    
    # Inicializar la base de datos con la app
    db.init_app(app)
    
    # Registrar los Blueprints
    app.register_blueprint(tienda_bp)
    app.register_blueprint(admin_bp)
    
    # Inicializar SocketIO (manage_session=False asegura que usemos la sesión nativa de Flask)
    socketio.init_app(app, cors_allowed_origins="*", manage_session=False)
    
    with app.app_context():
        # MEJORA: El "Parche Robusto" de SQL crudo fue eliminado. 
        # Ahora Flask-Migrate se encargará de los cambios de esquema limpiamente.
        db.create_all()

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

@socketio.on('enviar_mensaje')
def handle_mensaje(data):
    from model import Mensaje
    from db import db
    
    # SOLUCIÓN SPOOFING: Obtenemos el remitente desde la sesión segura
    remitente_id = session.get('user_id')
    if not remitente_id:
        return # Si no hay sesión, abortar operación silenciosamente (o emitir error)
    
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
        if tipo == 'todos' and msg.remitente_id == user_id:
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

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)