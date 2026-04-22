# Nombre del archivo: routes.py
from flask import Blueprint, render_template, request, jsonify, current_app, flash, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeSerializer
from db import db
from model import Usuario, Mensaje, Invitacion
import os
from werkzeug.utils import secure_filename
import uuid
import random
import string

# Configuración de subida de archivos
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# NUEVO: Se agregaron pptx, xls, html a los formatos permitidos para la Sala Virtual
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'pdf', 'txt', 'docx', 'json', 'zip', 'svg', 'pptx', 'xls', 'html'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

tienda_bp = Blueprint('tienda', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_serializer():
    return URLSafeSerializer(current_app.config['SECRET_KEY'])

@tienda_bp.route('/')
def inicio():
    if session.get('user_id'):
        return redirect(url_for('tienda.chat'))
    return render_template('inicio.html')

@tienda_bp.route('/tienda')
def tienda():
    return render_template('tienda.html')

@tienda_bp.route('/chat')
def chat():
    if not session.get('user_id'):
        flash("Debes iniciar sesión para acceder al chat.", "error")
        return redirect(url_for('tienda.login'))
    return render_template('chat.html')

@tienda_bp.route('/api/usuarios_chat')
def api_usuarios_chat():
    try:
        usuarios = Usuario.query.all()
        # Ocultamos a los invitados temporales de la lista de contactos globales
        return jsonify([u.to_dict() for u in usuarios if not (u.opciones_extra and u.opciones_extra.get('is_guest'))])
    except Exception as e:
        print(f"Error en api_usuarios_chat: {e}")
        return jsonify({"error": str(e)}), 500

@tienda_bp.route('/api/mensajes/<destinatario>')
def api_mensajes_privados(destinatario):
    try:
        mi_id = session.get('user_id')
        if not mi_id:
            return jsonify([])
            
        mi_id_str = str(mi_id)
        
        if destinatario == 'global':
            mensajes_crudos = Mensaje.query.filter_by(destinatario_id=None).order_by(Mensaje.fecha_envio).all()
        else:
            mensajes_crudos = Mensaje.query.filter(
                ((Mensaje.remitente_id == mi_id_str) & (Mensaje.destinatario_id == destinatario)) |
                ((Mensaje.remitente_id == destinatario) & (Mensaje.destinatario_id == mi_id_str))
            ).order_by(Mensaje.fecha_envio).all()
            
        mensajes_filtrados = []
        for m in mensajes_crudos:
            if any(u.id == mi_id for u in m.oculto_para_usuarios):
                continue
            mensajes_filtrados.append(m.to_dict())
                
        return jsonify(mensajes_filtrados)
    except Exception as e:
        print(f"Error en api_mensajes_privados: {e}")
        return jsonify({"error": str(e)}), 500

@tienda_bp.route('/api/upload_file', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': f'Tipo de archivo no permitido. Extensiones válidas: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(filepath)
    
    return jsonify({
        'url': url_for('static', filename=f'uploads/{unique_filename}'),
        'tipo': file.content_type,
        'nombre': filename
    })

# ========================================================
# NUEVO: RUTAS DE SALA VIRTUAL Y LLAVES DE INVITACIÓN
# ========================================================
@tienda_bp.route('/api/generar_invitacion', methods=['POST'])
def generar_invitacion():
    if not session.get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.json
    codigo = "SALA-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    inv = Invitacion(
        codigo=codigo,
        fecha_actividad=data.get('fecha'),
        hora_actividad=data.get('hora'),
        capacidad=int(data.get('capacidad')),
        creador_id=session.get('user_id')
    )
    db.session.add(inv)
    db.session.commit()
    
    return jsonify({'status': 'success', 'codigo': codigo})

@tienda_bp.route('/api/finalizar_invitacion', methods=['POST'])
def finalizar_invitacion():
    if not session.get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    
    codigo = request.json.get('codigo')
    inv = Invitacion.query.filter_by(codigo=codigo).first()
    if inv:
        inv.activa = False
        db.session.commit()
    return jsonify({'status': 'success'})

@tienda_bp.route('/api/login_invitado', methods=['POST'])
def login_invitado():
    data = request.json
    codigo = data.get('codigo')
    nombre = data.get('nombre')
    
    inv = Invitacion.query.filter_by(codigo=codigo).first()
    if not inv or not inv.activa:
        return jsonify({'status': 'error', 'mensaje': 'Esta llave es obsoleta o está mal digitada.'}), 400
    
    # Creamos un usuario temporal
    nuevo_guest = Usuario(
        nombre=nombre,
        primer_apellido="(Invitado)",
        segundo_apellido="",
        telefono="00000000",
        email=f"guest_{uuid.uuid4().hex[:8]}@guest.com", 
        password=generate_password_hash("guest"),
        opciones_extra={'is_guest': True, 'tema': 'tema-default'}
    )
    db.session.add(nuevo_guest)
    db.session.commit()
    
    session['user_id'] = nuevo_guest.id
    session['user_nombre'] = nuevo_guest.nombre
    session['tema'] = 'tema-default'
    return jsonify({'status': 'success', 'redirect': '/lobby'})

@tienda_bp.route('/api/hacer_admin', methods=['POST'])
def hacer_admin():
    if not session.get('is_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    user_id = request.json.get('user_id')
    usr = Usuario.query.get(user_id)
    if usr:
        opc = usr.opciones_extra or {}
        opc['is_admin'] = True
        usr.opciones_extra = opc
        db.session.merge(usr)
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'error': 'User not found'}), 404

# ========================================================
# RUTAS DE AUTENTICACIÓN Y TEMAS (EXISTENTES)
# ========================================================

@tienda_bp.route('/api/guardar_tema', methods=['POST'])
def guardar_tema():
    tema = request.json.get('tema')
    mi_id = session.get('user_id')
    session['tema'] = tema 
    
    if mi_id and tema:
        usuario = Usuario.query.get(mi_id)
        if usuario:
            opciones = usuario.opciones_extra or {}
            opciones['tema'] = tema
            usuario.opciones_extra = opciones
            db.session.merge(usuario)
            db.session.commit()
    return jsonify({'status': 'success'})

@tienda_bp.route('/api/guardar_gif', methods=['POST'])
def guardar_gif():
    mi_id = session.get('user_id')
    url_gif = request.json.get('url')
    if mi_id and url_gif:
        usuario = Usuario.query.get(mi_id)
        opciones = usuario.opciones_extra or {}
        gifs = opciones.get('gifs_guardados', [])
        if url_gif not in gifs:
            gifs.append(url_gif)
            opciones['gifs_guardados'] = gifs
            usuario.opciones_extra = opciones
            db.session.merge(usuario)
            db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Failed'}), 400

@tienda_bp.route('/login', methods=['GET'])
def login():
    if session.get('user_id'):
        return redirect(url_for('tienda.chat'))
    return render_template('login.html')

@tienda_bp.route('/registro', methods=['GET'])
def registro():
    if session.get('user_id'):
        return redirect(url_for('tienda.chat'))
    return render_template('registro.html')

@tienda_bp.route('/api/registro', methods=['POST'])
def api_registro():
    data = request.json
    hashed_pwd = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    opciones = data.get('opciones_extra', {})
    opciones['tema'] = session.get('tema', 'tema-default')

    nuevo_usuario = Usuario(
        nombre=data['nombre'],
        primer_apellido=data['primer_apellido'],
        segundo_apellido=data['segundo_apellido'],
        telefono=data['telefono'],
        email=data['email'], 
        password=hashed_pwd,
        opciones_extra=opciones
    )
    
    db.session.add(nuevo_usuario)
    db.session.commit()

    s = get_serializer()
    llave_encriptada = s.dumps({ "id": nuevo_usuario.id, "email": nuevo_usuario.email })

    return jsonify({
        "status": "success", 
        "mensaje": "Usuario registrado exitosamente",
        "llave_json": {"llave_acceso": llave_encriptada},
        "user_id": nuevo_usuario.id
    })

@tienda_bp.route('/api/login_llave', methods=['POST'])
def api_login_llave():
    data = request.json
    llave_encriptada = data.get('llave_acceso')
    if not llave_encriptada:
        return jsonify({"status": "error", "mensaje": "Llave inválida"}), 400
        
    s = get_serializer()
    try:
        info_usuario = s.loads(llave_encriptada)
        usuario = Usuario.query.get(info_usuario['id'])
        if usuario and usuario.email == info_usuario['email']:
            session['user_id'] = usuario.id
            session['user_nombre'] = usuario.nombre
            session['tema'] = usuario.opciones_extra.get('tema', 'tema-default') if usuario.opciones_extra else 'tema-default'
            session['is_admin'] = usuario.opciones_extra.get('is_admin', False) if usuario.opciones_extra else False
            return jsonify({"status": "success", "mensaje": "Login exitoso mediante llave", "redirect": "/chat"})
    except Exception:
        return jsonify({"status": "error", "mensaje": "Llave corrupta o no autorizada"}), 403
    return jsonify({"status": "error", "mensaje": "Usuario no encontrado"}), 404

@tienda_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    usuario = Usuario.query.filter_by(email=data.get('email')).first()
    if usuario and check_password_hash(usuario.password, data.get('password')):
        session['user_id'] = usuario.id
        session['user_nombre'] = usuario.nombre
        session['tema'] = usuario.opciones_extra.get('tema', 'tema-default') if usuario.opciones_extra else 'tema-default'
        session['is_admin'] = usuario.opciones_extra.get('is_admin', False) if usuario.opciones_extra else False
        return jsonify({"status": "success", "mensaje": f"Bienvenido, {usuario.nombre}.", "redirect": "/chat"})
    return jsonify({"status": "error", "mensaje": "Email o contraseña incorrectos."}), 401

@tienda_bp.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión exitosamente.", "info")
    return redirect(url_for('tienda.inicio'))

@admin_bp.route('/')
def dashboard():
    return render_template('admin/dashboard.html', total_usuarios=Usuario.query.count())

@admin_bp.route('/usuarios')
def lista_usuarios():
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@tienda_bp.route('/lobby')
def lobby():
    if not session.get('user_id'):
        flash("Debes iniciar sesión para entrar a la sala.", "error")
        return redirect(url_for('tienda.login'))
    return render_template('lobby.html')