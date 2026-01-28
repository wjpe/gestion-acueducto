from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Socio(db.Model):
    __tablename__ = 'socios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación: Un socio puede tener varios predios
    predios = db.relationship('Predio', backref='dueno', lazy=True)

class Predio(db.Model):
    __tablename__ = 'predios'
    id = db.Column(db.Integer, primary_key=True)
    numero_cuenta = db.Column(db.String(20), unique=True, nullable=False)
    serial_medidor = db.Column(db.String(50))
    sector = db.Column(db.String(50))  # Útil para análisis de racionamiento
    estado = db.Column(db.String(20), default='Activo') # Activo, Suspendido, Corte
    socio_id = db.Column(db.Integer, db.ForeignKey('socios.id'), nullable=False)
    
    # Relación: Un predio tiene muchas lecturas
    lecturas = db.relationship('Lectura', backref='predio', lazy=True)

class Lectura(db.Model):
    __tablename__ = 'lecturas'
    id = db.Column(db.Integer, primary_key=True)
    predio_id = db.Column(db.Integer, db.ForeignKey('predios.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False) # 1 al 12
    anio = db.Column(db.Integer, nullable=False)
    lectura_anterior = db.Column(db.Float, nullable=False)
    lectura_actual = db.Column(db.Float, nullable=False)
    consumo_mes = db.Column(db.Float, nullable=False) # Calculado: Actual - Anterior
    fecha_toma = db.Column(db.DateTime, default=datetime.utcnow)

class ConfiguracionTarifa(db.Model):
    __tablename__ = 'tarifas'
    id = db.Column(db.Integer, primary_key=True)
    cargo_fijo = db.Column(db.Float, nullable=False)
    limite_basico = db.Column(db.Float, nullable=False) # m3 incluidos
    valor_m3_extra = db.Column(db.Float, nullable=False)
    fecha_desde = db.Column(db.DateTime, default=datetime.utcnow)
    activa = db.Column(db.Boolean, default=True)