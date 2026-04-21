# Nombre del archivo: model.py
from db import db
from datetime import datetime, timezone

# MEJORA: Tabla intermedia para evitar el Anti-Patrón del CSV en la DB.
# Relación Muchos-a-Muchos entre Mensajes y Usuarios que los ocultaron.
mensajes_ocultos = db.Table('mensajes_ocultos',
    db.Column('mensaje_id', db.Integer, db.ForeignKey('mensajes.id'), primary_key=True),
    db.Column('usuario_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class Usuario(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(8), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) 
    
    opciones_extra = db.Column(db.JSON, nullable=True) 
    
    # MEJORA: Zonas Horarias en UTC (estándar de la industria)
    fecha_registro = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'apellidos': f"{self.primer_apellido} {self.segundo_apellido}",
            'telefono': self.telefono,
            'email': self.email,
            'opciones_extra': self.opciones_extra,
            'fecha_registro': self.fecha_registro.isoformat()
        }

class Mensaje(db.Model):
    __tablename__ = 'mensajes'
    
    id = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 
    
    texto = db.Column(db.Text, nullable=True)
    archivo_url = db.Column(db.String(255), nullable=True)
    tipo_archivo = db.Column(db.String(50), nullable=True)
    nombre_archivo = db.Column(db.String(255), nullable=True)
    
    # MEJORA: Guardamos en UTC
    fecha_envio = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    leido = db.Column(db.Boolean, default=False)
    borrado = db.Column(db.Boolean, default=False)
    
    remitente = db.relationship('Usuario', foreign_keys=[remitente_id])
    
    # MEJORA: Reemplazamos la columna de texto "oculto_para" por la relación relacional correcta
    oculto_para_usuarios = db.relationship('Usuario', secondary=mensajes_ocultos, lazy='subquery',
                                           backref=db.backref('mensajes_ocultos', lazy=True))

    def to_dict(self):
        # Nota: Idealmente el frontend convertiría el UTC a local usando JavaScript (Intl.DateTimeFormat),
        # pero mantenemos el strftime para no romper tu lógica actual del frontend.
        return {
            'id': self.id,
            'remitente_id': self.remitente_id,
            'remitente_nombre': self.remitente.nombre if self.remitente else 'Desconocido',
            'destinatario_id': self.destinatario_id,
            'texto': self.texto,
            'archivo_url': self.archivo_url,
            'tipo_archivo': self.tipo_archivo,
            'nombre_archivo': self.nombre_archivo,
            'fecha_envio': self.fecha_envio.strftime('%I:%M %p') if self.fecha_envio else '',
            'leido': self.leido,
            'borrado': self.borrado
        }