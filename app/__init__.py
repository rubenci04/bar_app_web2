import os
from flask import Flask, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import datetime
import click

# Inicialización de extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

DB_NAME = "bar_app.db"

def create_app():
    app = Flask(__name__, 
                instance_relative_config=True, 
                static_folder='static', 
                template_folder='templates')
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'una-llave-secreta-muy-dificil-de-adivinar')
    
    # Crear el directorio de instancia si no existe
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, DB_NAME)}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, inicie sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'

    @app.context_processor
    def utility_processor():
        # Función para generar el token CSRF que será accesible en todas las plantillas
        def get_csrf_token():
            return generate_csrf()
        return dict(csrf_token=get_csrf_token)

    from .auth import auth_bp
    from .admin import admin_bp
    from .mozo import mozo_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(mozo_bp, url_prefix='/mozo')
    
    from .models import User, Product, Table, Order

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.cli.command("seed-db")
    def seed_db_command():
        """Crea los datos iniciales para la base de datos."""
        with app.app_context():
            if User.query.first() is not None:
                print("La base de datos ya tiene datos. Abortando.")
                return

            print("Base de datos vacía. Creando datos iniciales...")
            
            # Crear usuarios
            admin = User(username="admin", role='admin')
            admin.set_password("admin123")
            mozo = User(username="mozo", role='mozo')
            mozo.set_password("mozo123")
            db.session.add_all([admin, mozo])
            print("-> Usuarios 'admin' y 'mozo' creados.")

            # Crear productos
            products_to_add = [
                Product(name="Muzzarella", price=7000.00, type="Pizzas", stock=100),
                Product(name="Especial Don Enrique", price=10500.00, type="Pizzas", stock=50),
                Product(name="Lomo Clásico", price=6500.00, type="Sandwiches", stock=80),
                Product(name="Hamburguesa con Cheddar", price=5400.00, type="Hamburguesas", stock=120),
                Product(name="Milanesa Napolitana", price=7200.00, type="Milanesas al Plato", stock=60),
                Product(name="Papas Fritas Clásicas", price=3000.00, type="Papas Fritas", stock=200),
                Product(name="Cerveza Lager (1L)", price=2500.00, type="Bebidas con Alcohol", stock=150),
                Product(name="Gaseosa Línea Coca-Cola", price=1500.00, type="Bebidas sin Alcohol", stock=300),
                Product(name="Flan con Dulce de Leche", price=2200.00, type="Postre", stock=40)
            ]
            db.session.add_all(products_to_add)
            print(f"-> {len(products_to_add)} productos creados.")

            # Crear mesas
            tables_to_add = [ Table(number=i, capacity=4 if i % 2 == 0 else 2, status='Vacía') for i in range(1, 11) ]
            db.session.add_all(tables_to_add)
            print(f"-> {len(tables_to_add)} mesas creadas.")
            
            db.session.commit()
            print("\n¡Base de datos inicializada con éxito!")
            print("Credenciales por defecto:")
            print("  Admin: admin / admin123")
            print("  Mozo:  mozo / mozo123\n")
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('mozo.tables_view'))
        return redirect(url_for('auth.login'))
        
    return app