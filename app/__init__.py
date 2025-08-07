import os
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
import click

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

DB_NAME = "bar_app.db"

def create_app():
    # --- CORRECCIÓN DEFINITIVA ---
    # Le decimos a Flask explícitamente dónde están las plantillas y los archivos estáticos.
    app = Flask(__name__, 
                instance_relative_config=True, 
                static_folder='static', 
                template_folder='templates')
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'una-llave-secreta-muy-dificil-de-adivinar')
    
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, DB_NAME)}'
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @app.context_processor
    def utility_processor():
        def get_cache_version():
            return int(datetime.now().timestamp())
        return dict(cache_version=get_cache_version)

    from .auth import auth_bp
    from .admin import admin_bp
    from .mozo import mozo_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(mozo_bp, url_prefix='/mozo')
    
    from .models import User, Product, Table
    from werkzeug.security import generate_password_hash

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.cli.command("seed-db")
    def seed_db_command():
        """Crea los datos iniciales para la base de datos."""
        if User.query.first() is not None:
            print("La base de datos ya tiene datos. Abortando.")
            return

        print("Base de datos vacía. Creando datos iniciales...")
        admin = User(username="admin", password_hash=generate_password_hash("password123"), role='admin')
        db.session.add(admin)
        print("-> Usuario 'admin' creado.")

        products_to_add = [
            Product(name="Muzzarella", price=7000.00, type="Pizzas", stock=100),
            Product(name="Especial Don Enrique Pizza", price=10500.00, type="Pizzas", stock=100),
            Product(name="Lomo Comun", price=6500.00, type="Sandwiches", stock=100),
            Product(name="Panceta y Cheddar", price=5400.00, type="Sandwiches", stock=100)
        ]
        db.session.add_all(products_to_add)
        print(f"-> {len(products_to_add)} productos creados.")

        tables_to_add = [
            Table(number=1, capacity=4, status='Vacía'),
            Table(number=2, capacity=4, status='Vacía'),
            Table(number=3, capacity=2, status='Vacía')
        ]
        db.session.add_all(tables_to_add)
        print(f"-> {len(tables_to_add)} mesas creadas.")
        
        db.session.commit()
        print("¡Base de datos inicializada con éxito!")

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('mozo.tables_view'))
        return redirect(url_for('auth.login'))

    return app