# =======================================================
# 1. IMPORTACIONES NECESARIAS
# =======================================================
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash # Para seguridad de contraseñas

# =======================================================
# 2. CONFIGURACIÓN INICIAL
# =======================================================
app = Flask(__name__)

# Configuración de la aplicación
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui' # NECESARIO para sesiones y flash
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///asistencia_segura.db' # Base de datos local
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialización de extensiones
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Define la ruta de login

# Función para cargar el usuario (necesaria para Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    # La clave primaria para Profesor es su ID.
    return Profesor.query.get(int(user_id))

# =======================================================
# 3. MODELOS DE LA BASE DE DATOS (SQLite)
# =======================================================

# Modelo para el Profesor (Usuario que accede al dashboard)
class Profesor(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Modelo para los Registros de Asistencia
class Asistencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clase_id = db.Column(db.String(50), nullable=False) # ID único de la clase (ej: "Matematica_101")
    apellido = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), nullable=False) # Usado para la validación anti-duplicado
    fecha = db.Column(db.DateTime, default=datetime.utcnow) # Fecha y hora del registro

# =======================================================
# 4. RUTAS Y LÓGICA DEL SERVIDOR
# =======================================================

# -------------------------------------------------------
# Ruta 1: Login del Profesor
# -------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Si ya está logueado, redirige al dashboard
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        usuario_form = request.form.get('usuario')
        contrasena_form = request.form.get('contrasena')

        profesor = Profesor.query.filter_by(usuario=usuario_form).first()

        # Verifica si el profesor existe y si la contraseña es correcta
        if profesor and profesor.check_password(contrasena_form):
            login_user(profesor)
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')

    # Muestra el formulario de login (login.html)
    return render_template('login.html')

# -------------------------------------------------------
# Ruta 2: Dashboard del Profesor (Requiere Login)
# -------------------------------------------------------
@app.route('/dashboard')
@login_required # Esta ruta solo es accesible si el usuario está logueado
def dashboard():
    # Obtiene todos los registros de asistencia, ordenados por fecha descendente
    registros = Asistencia.query.order_by(Asistencia.fecha.desc()).all()
    # Pasa los registros a la plantilla para mostrarlos en la tabla
    return render_template('profesor_dashboard.html', registros=registros)

# -------------------------------------------------------
# Ruta 3: Formulario de Asistencia del Alumno (Validación Única)
# -------------------------------------------------------
@app.route('/asistencia/<clase_id>', methods=['GET', 'POST'])
def asistencia(clase_id):
    if request.method == 'POST':
        dni_form = request.form.get('dni')
        apellido_form = request.form.get('apellido')
        nombre_form = request.form.get('nombre')

        # 1. VALIDACIÓN ANTI-DUPLICADO:
        # Verifica si ya existe un registro para este DNI en ESTA CLASE para HOY
        
        # Define el inicio y fin del día de hoy (UTC)
        hoy = datetime.utcnow().date()
        inicio_del_dia = datetime.combine(hoy, datetime.min.time())
        fin_del_dia = datetime.combine(hoy, datetime.max.time())
        
        registro_existente = Asistencia.query.filter(
            Asistencia.dni == dni_form,
            Asistencia.clase_id == clase_id,
            Asistencia.fecha.between(inicio_del_dia, fin_del_dia)
        ).first()

        if registro_existente:
            # Si el registro existe, flashea una advertencia y no guarda.
            flash(f'ADVERTENCIA: El DNI {dni_form} ya marcó asistencia para la clase {clase_id} hoy.', 'warning')
        else:
            # 2. REGISTRO NUEVO:
            nuevo_registro = Asistencia(
                clase_id=clase_id,
                apellido=apellido_form.upper(), # Guarda en mayúsculas para consistencia
                nombre=nombre_form.title(),    # Guarda con capitalización
                dni=dni_form
            )
            db.session.add(nuevo_registro)
            db.session.commit()
            flash('¡Asistencia registrada con éxito! Gracias.', 'success')

        # Redirige de vuelta al formulario (para mostrar el mensaje flash)
        return redirect(url_for('asistencia', clase_id=clase_id))

    # Muestra el formulario de asistencia (asistencia_form.html)
    # Pasa el ID de la clase para mostrarlo en el título
    return render_template('asistencia_form.html', clase_id=clase_id)

# -------------------------------------------------------
# Ruta 4: Cerrar Sesión
# -------------------------------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))


# -------------------------------------------------------
# Ruta Raíz (Redirección por defecto)
# -------------------------------------------------------
@app.route('/')
def index():
    # Redirige la ruta principal a la página de login
    return redirect(url_for('login'))

# =======================================================
# 5. INICIALIZACIÓN DEL SERVIDOR Y BASE DE DATOS
# =======================================================
if __name__ == '__main__':
    with app.app_context():
        # Crea la base de datos y las tablas si no existen
        db.create_all()

        # Opcional: Crear un usuario inicial para pruebas si no existe
        if Profesor.query.filter_by(usuario='profesor').first() is None:
            admin_user = Profesor(usuario='profesor')
            admin_user.set_password('password123')
            db.session.add(admin_user)
            db.session.commit()
            print("\n--- Usuario de prueba creado: profesor / password123 ---\n")

    # Esta línea DEBE estar al final.
    app.run(debug=True)
    # Codigo que hace arrancar en programa, Este debe ser ejecutado en la terminal.
    #   .\venv\Scripts\python -m flask --app app run