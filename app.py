from flask import Flask, render_template, request, redirect, url_for, flash, Response
from models import db, Socio, Predio, Lectura, ConfiguracionTarifa, Usuario
from datetime import datetime
import os
import io
import re
import csv
from io import TextIOWrapper
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate



app = Flask(__name__)

# CONFIGURACIÓN
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'acueducto.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# NECESARIO PARA MENSAJES FLASH (Validaciones)
app.secret_key = 'mi_clave_secreta_segura' 

db.init_app(app)

with app.app_context():
    db.create_all()
    if not ConfiguracionTarifa.query.first():
        # ... (código de tarifa inicial igual al anterior) ...
        pass

# --- RUTAS ---

@app.route('/')
@login_required # <--- Solo usuarios registrados pueden entrar
def index():
    total_socios = Socio.query.count()
    total_predios = Predio.query.count()
    # Enviamos ambas variables al template
    return render_template('index.html', socios=total_socios, predios=total_predios)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# RUTA LOGIN (Simplificada para empezar)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = Usuario.query.filter_by(username=username).first()
        
        # IMPORTANTE: Usamos el método check_password para comparar hashes
        if user and user.check_password(password):
            login_user(user)
            flash('Bienvenido al sistema Aguamir', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login.html'))


@app.route('/socio/nuevo', methods=['GET', 'POST'])
@login_required # <--- Solo usuarios registrados pueden entrar
def nuevo_socio():
    if request.method == 'POST':
        # 1. Capturamos los datos
        nombre = request.form['nombre'].strip()
        cedula_raw = request.form['cedula'].strip()
        telefono_raw = request.form['telefono'].strip()

        # 2. SANITIZACIÓN (Limpieza profunda)
        # re.sub(r'\D', '', texto) -> Busca todo lo que NO sea dígito (\D) y reemplázalo por nada ('')
        cedula_limpia = re.sub(r'\D', '', cedula_raw)
        telefono_limpio = re.sub(r'\D', '', telefono_raw)

        # 3. VALIDACIONES ESTRICTAS
        
        # Validación A: Cédula vacía después de limpiar (ej: el usuario escribió solo "abc")
        if not cedula_limpia:
            flash('Error: La cédula no es válida. Debe contener números.', 'danger')
            return redirect(url_for('nuevo_socio'))
            
        # Validación B: Teléfono con letras que no pudimos limpiar o vacío
        # Si el usuario escribió algo en el campo original, pero al limpiar quedó vacío, era basura.
        if telefono_raw and not telefono_limpio:
             flash('Error: El teléfono ingresado no contiene números válidos.', 'danger')
             return redirect(url_for('nuevo_socio'))

        # Validación C: Duplicados (Usamos la cédula limpia)
        if Socio.query.filter_by(cedula=cedula_limpia).first():
            flash('Error: Esa cédula ya existe.', 'warning')
            return redirect(url_for('nuevo_socio'))

        # 4. GUARDADO (Guardamos SOLAMENTE la versión limpia)
        try:
            nuevo = Socio(
                nombre=nombre, 
                cedula=cedula_limpia,   # <--- Guardamos la limpia
                telefono=telefono_limpio # <--- Guardamos el limpio
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Socio creado exitosamente.', 'success')
            return redirect(url_for('lista_socios'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error de base de datos: {str(e)}', 'danger')
            return redirect(url_for('nuevo_socio'))

    return render_template('nuevo_socio.html')

# --- LISTAR SOCIOS ---
@app.route('/socios')
@login_required # <--- Solo usuarios registrados pueden entrar
def lista_socios():
    todos_los_socios = Socio.query.order_by(Socio.nombre).all()
    return render_template('lista_socios.html', socios=todos_los_socios)

# --- EDITAR SOCIO ---
@app.route('/socio/editar/<int:id>', methods=['GET', 'POST'])
@login_required # <--- Solo usuarios registrados pueden entrar
def editar_socio(id):
    socio = Socio.query.get_or_404(id)
    
    if request.method == 'POST':
        socio.nombre = request.form['nombre']
        socio.telefono = request.form['telefono']
        # La cédula generalmente no se edita por seguridad, 
        # pero si lo necesitas, puedes agregarla aquí.
        
        db.session.commit()
        flash('Datos actualizados correctamente', 'success')
        return redirect(url_for('lista_socios'))
    
    return render_template('editar_socio.html', socio=socio)


@app.route('/predio/nuevo', methods=['GET', 'POST'])
@login_required # <--- Solo usuarios registrados pueden entrar
def nuevo_predio():
    # Consultamos todos los socios para el menú desplegable
    socios = Socio.query.order_by(Socio.nombre).all()
    
    if request.method == 'POST':
        numero_cuenta = request.form['numero_cuenta'].strip()
        serial_medidor = request.form['serial_medidor'].strip()
        sector = request.form['sector']
        socio_id = request.form['socio_id']

        # Validación: El número de cuenta debe ser único
        existe = Predio.query.filter_by(numero_cuenta=numero_cuenta).first()
        if existe:
            flash('Error: El número de cuenta ya está asignado a otro predio.', 'danger')
            return redirect(url_for('nuevo_predio'))

        nuevo = Predio(
            numero_cuenta=numero_cuenta,
            serial_medidor=serial_medidor,
            sector=sector,
            socio_id=socio_id
        )
        
        try:
            db.session.add(nuevo)
            db.session.commit()
            flash('Predio registrado exitosamente.', 'success')
            return redirect(url_for('lista_predios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar predio: {str(e)}', 'danger')

    return render_template('nuevo_predio.html', socios=socios)

@app.route('/predios')
@login_required # <--- Solo usuarios registrados pueden entrar
def lista_predios():
    predios = Predio.query.all()
    return render_template('lista_predios.html', predios=predios)

@app.route('/predio/editar/<int:id>', methods=['GET', 'POST'])
@login_required # <--- Solo usuarios registrados pueden entrar
def editar_predio(id):
    predio = Predio.query.get_or_404(id)
    socios = Socio.query.order_by(Socio.nombre).all()
    
    if request.method == 'POST':
        predio.serial_medidor = request.form['serial_medidor'].strip()
        predio.sector = request.form['sector']
        predio.estado = request.form['estado']
        predio.socio_id = request.form['socio_id']
        
        db.session.commit()
        flash('Predio actualizado con éxito', 'success')
        return redirect(url_for('lista_predios'))
    
    return render_template('editar_predio.html', predio=predio, socios=socios)

@app.route('/socio/<int:id>/predios')
@login_required # <--- Solo usuarios registrados pueden entrar
def ver_predios_socio(id):
    socio = Socio.query.get_or_404(id)
    # Gracias a backref='predios', podemos hacer esto:
    predios = socio.predios 
    return render_template('lista_predios.html', predios=predios, socio_nombre=socio.nombre)

# --- RUTA PARA REGISTRAR LECTURA ---
@app.route('/lectura/nueva/<int:id>', methods=['GET', 'POST'])
@login_required # <--- Solo usuarios registrados pueden entrar
def registrar_lectura(id):
    predio = Predio.query.get_or_404(id)
    
    # Buscamos la última lectura para este predio
    ultima = Lectura.query.filter_by(predio_id=id).order_by(Lectura.id.desc()).first()
    lectura_anterior = ultima.lectura_actual if ultima else 0

    if request.method == 'POST':
        # Capturamos y validamos que sea número
        valor_input = request.form.get('lectura_actual', '0')
        try:
            lectura_act = float(valor_input)
        except ValueError:
            flash('Error: Ingrese un número válido.', 'danger')
            return redirect(url_for('registrar_lectura', id=id))
        
        if lectura_act < lectura_anterior:
            flash(f'La lectura actual ({lectura_act}) no puede ser menor a la anterior ({lectura_anterior})', 'danger')
            return redirect(url_for('registrar_lectura', id=id))

        consumo = lectura_act - lectura_anterior
        
        # Guardado en base de datos
        nueva = Lectura(
            predio_id=id,
            mes=datetime.now().month,
            anio=datetime.now().year,
            lectura_anterior=lectura_anterior,
            lectura_actual=lectura_act,
            consumo_mes=consumo
        )
        
        db.session.add(nueva)
        db.session.commit()
        flash('Lectura registrada correctamente', 'success')
        return redirect(url_for('lista_predios'))

    return render_template('nueva_lectura.html', predio=predio, lectura_anterior=lectura_anterior)


@app.route('/predio/<int:id>/historial')
@login_required # <--- Solo usuarios registrados pueden entrar
def historial_predio(id):
    predio = Predio.query.get_or_404(id)
    # Traemos las lecturas de la más reciente a la más antigua
    lecturas = Lectura.query.filter_by(predio_id=id).order_by(Lectura.anio.desc(), Lectura.mes.desc()).all()
    return render_template('historial_lecturas.html', predio=predio, lecturas=lecturas)


# --- RUTA PARA CARGA MASIVA DE LECTURAS ---
@app.route('/lectura/carga-masiva', methods=['GET', 'POST'])
@login_required # <--- Solo usuarios registrados pueden entrar
def carga_masiva():
    if request.method == 'POST':
        if 'archivo_csv' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
            
        archivo = request.files['archivo_csv']
        
        if archivo.filename == '':
            flash('El archivo no tiene nombre', 'danger')
            return redirect(request.url)

        try:
            stream = io.StringIO(archivo.stream.read().decode("UTF8"), newline=None)
            lector = csv.DictReader(stream)
            
            exitos = 0
            errores = []
            mes_actual = datetime.now().month
            anio_actual = datetime.now().year

            for fila in lector:
                cuenta = fila['numero_cuenta'].strip()
                lectura_str = fila['lectura_actual'].strip()
                
                if not lectura_str: continue # Saltar filas vacías

                predio = Predio.query.filter_by(numero_cuenta=cuenta).first()
                if predio:
                    lectura_val = float(lectura_str)
                    # Obtener anterior
                    ult = Lectura.query.filter_by(predio_id=predio.id).order_by(Lectura.id.desc()).first()
                    anterior = ult.lectura_actual if ult else 0
                    
                    if lectura_val >= anterior:
                        nueva = Lectura(
                            predio_id=predio.id,
                            mes=mes_actual,
                            anio=anio_actual,
                            lectura_anterior=anterior,
                            lectura_actual=lectura_val,
                            consumo_mes=lectura_val - anterior
                        )
                        db.session.add(nueva)
                        exitos += 1
                    else:
                        errores.append(f"Cuenta {cuenta}: Lectura menor a la anterior.")
                else:
                    errores.append(f"Cuenta {cuenta}: No encontrada.")

            db.session.commit()
            
            if errores:
                for err in errores[:5]: # Mostrar solo los primeros 5 errores
                    flash(err, 'warning')
            
            flash(f'Carga completada. {exitos} registros exitosos.', 'success')
            return redirect(url_for('lista_predios'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error procesando el archivo: {str(e)}', 'danger')

    return render_template('carga_masiva.html')

# --- RUTA PARA DESCARGAR CSV PARA CARGA MASIVA DE LECTURAS ---
@app.route('/lectura/descargar-plantilla')
@login_required # <--- Solo usuarios registrados pueden entrar
def descargar_plantilla():
    # Obtener todos los predios
    predios = Predio.query.all()
    
    # Crear un buffer en memoria para el CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Encabezados: Incluimos datos de referencia para que el operario no se pierda
    writer.writerow(['numero_cuenta', 'socio', 'serial_medidor', 'lectura_actual'])
    
    for p in predios:
        writer.writerow([p.numero_cuenta, p.dueno.nombre, p.serial_medidor, ''])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=plantilla_lecturas.csv"}
    )

# --- CARGA MASIVA DE SOCIOS ---
@app.route('/socio/carga-masiva', methods=['GET', 'POST'])
@login_required # <--- Solo usuarios registrados pueden entrar
def carga_masiva_socios():
    if request.method == 'POST':
        archivo = request.files['archivo_csv']
        stream = io.StringIO(archivo.stream.read().decode("UTF8"), newline=None)
        lector = csv.DictReader(stream)
        
        resultados = {'exitos': 0, 'errores': []}
        
        for fila in lector:
            try:
                nombre = fila['nombre'].strip()
                cedula = re.sub(r'\D', '', fila['cedula'])
                telefono = re.sub(r'\D', '', fila.get('telefono', ''))

                if not nombre or not cedula:
                    resultados['errores'].append(f"Fila omitida: Nombre o Cédula vacíos.")
                    continue

                if Socio.query.filter_by(cedula=cedula).first():
                    resultados['errores'].append(f"Socio {cedula}: Ya existe en el sistema.")
                    continue

                nuevo = Socio(nombre=nombre, cedula=cedula, telefono=telefono)
                db.session.add(nuevo)
                resultados['exitos'] += 1
            except Exception as e:
                resultados['errores'].append(f"Error inesperado: {str(e)}")

        db.session.commit()
        # Guardamos los resultados en la sesión para mostrarlos en la tabla resumen
        session['resumen_carga'] = resultados
        return redirect(url_for('resumen_carga_view', tipo='socios'))

    return render_template('carga_masiva_socios.html')

# --- VISTA DE RESUMEN ---
@app.route('/carga/resumen/<tipo>')
@login_required # <--- Solo usuarios registrados pueden entrar
def resumen_carga_view(tipo):
    resumen = session.get('resumen_carga', {'exitos': 0, 'errores': []})
    return render_template('resumen_carga.html', resumen=resumen, tipo=tipo)

@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    if current_user.rol != 'admin':
        flash('Acceso denegado. Solo administradores.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        rol = request.form['rol']

        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'warning')
        else:
            nuevo = Usuario(username=username, rol=rol)
            nuevo.set_password(password) # Encriptación automática
            db.session.add(nuevo)
            db.session.commit()
            flash(f'Usuario {username} creado con éxito.', 'success')
            return redirect(url_for('index'))

    return render_template('nuevo_usuario.html')



if __name__ == '__main__':
    app.run(debug=True)

