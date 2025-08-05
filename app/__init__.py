from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect # IMPORTANTE
import os
from werkzeug.security import generate_password_hash
from datetime import datetime

# ---- MENÚ INICIAL DE PRODUCTOS (COMO LO TENÍAS) ----
INITIAL_MENU_PRODUCTS = {
    "Sandwiches": [{"nombre": "Milanesa Común", "precio": 5300, "stock_inicial": 50}, {"nombre": "Lomo Común", "precio": 6500, "stock_inicial": 40}, {"nombre": "Lomo Cheddar", "precio": 6500, "stock_inicial": 40}, {"nombre": "Ternera Completa", "precio": 6500, "stock_inicial": 30}],
    "Hamburguesas": [{"nombre": "Simple", "precio": 4800, "stock_inicial": 60}, {"nombre": "Especial", "precio": 5400, "stock_inicial": 50}, {"nombre": "Roquefort", "precio": 6400, "stock_inicial": 30}, {"nombre": "Panceta y Cheddar", "precio": 5400, "stock_inicial": 40}, {"nombre": "Don Enrique Burger", "precio": 6200, "stock_inicial": 30}],
    "Pizzas": [{"nombre": "Muzzarella", "precio": 7000, "stock_inicial": 20}, {"nombre": "Jamón y Morrones", "precio": 8000, "stock_inicial": 15}, {"nombre": "Napolitana", "precio": 8000, "stock_inicial": 15}, {"nombre": "Fugazzetta", "precio": 8000, "stock_inicial": 10}, {"nombre": "Calabresa", "precio": 8000, "stock_inicial": 10}, {"nombre": "Roquefort Pizza", "precio": 8000, "stock_inicial": 10}, {"nombre": "Choclo Pizza", "precio": 8500, "stock_inicial": 10}, {"nombre": "Ternera Pizza", "precio": 10500, "stock_inicial": 8}, {"nombre": "Especial Don Enrique Pizza", "precio": 10500, "stock_inicial": 8}],
    "Milanesas al Plato": [{"nombre": "Napo P/1", "precio": 7600, "stock_inicial": 20}, {"nombre": "Napo P/2", "precio": 11800, "stock_inicial": 10}, {"nombre": "Mila Roquefort", "precio": 7600, "stock_inicial": 15}, {"nombre": "Mila Fugazzeta", "precio": 7600, "stock_inicial": 15}],
    "Tostados & Especiales": [{"nombre": "Tostado J&Q", "precio": 4800, "stock_inicial": 25}, {"nombre": "Tostado Ternera & Q", "precio": 5700, "stock_inicial": 20}, {"nombre": "Tostado Ternera Verdura & Q", "precio": 6000, "stock_inicial": 15}, {"nombre": "Mexicano (para 2)", "precio": 9000, "stock_inicial": 10}],
    "Papas Fritas": [{"nombre": "Papas Fritas Clásicas", "precio": 3200, "stock_inicial": 100}, {"nombre": "Papas Gratinadas (Cheddar/Tybo)", "precio": 4000, "stock_inicial": 30}, {"nombre": "Papas Don Enrique", "precio": 4600, "stock_inicial": 25}, {"nombre": "Papas Fritas (Porción Mediana)", "precio": 3200, "stock_inicial": 50}, {"nombre": "Papas Fritas (Porción Grande)", "precio": 4000, "stock_inicial": 50}],
    "Agregados": [{"nombre": "Jamón", "precio": 800, "stock_inicial": 100}, {"nombre": "Huevo", "precio": 800, "stock_inicial": 100}, {"nombre": "Panceta", "precio": 800, "stock_inicial": 80}, {"nombre": "Extra Papas (en plato)", "precio": 1400, "stock_inicial": 50}, {"nombre": "Roquefort o Cheddar", "precio": 800, "stock_inicial": 50}, {"nombre": "Cebolla Caramelizada", "precio": 600, "stock_inicial": 40}, {"nombre": "Extra Medallón Carne", "precio": 1800, "stock_inicial": 30}],
    "Bebidas con Alcohol": [{"nombre": "Cerveza Quilmes/Salta 1L", "precio": 4800, "stock_inicial": 100}, {"nombre": "Lata Cerveza (Quilmes/Salta/Imp.)", "precio": 2800, "stock_inicial": 150}, {"nombre": "Cerveza Imperial 1L", "precio": 5000, "stock_inicial": 80}, {"nombre": "Cerveza Norte 1L", "precio": 4500, "stock_inicial": 70}, {"nombre": "Smirnoff Ice Lata", "precio": 2900, "stock_inicial": 60}, {"nombre": "Vino Tinto 3/4 (Consultar)", "precio": 4700, "stock_inicial": 30}],
    "Bebidas sin Alcohol": [{"nombre": "Gaseosa Línea Pepsi 2L", "precio": 3800, "stock_inicial": 100}, {"nombre": "Agua Mineral 500ml", "precio": 2500, "stock_inicial": 120}, {"nombre": "Jugo Natural", "precio": 3000, "stock_inicial": 50}, {"nombre": "Gaseosa Línea Coca-Cola Lata", "precio": 2800, "stock_inicial": 100}, {"nombre": "Gaseosa Línea Pepsi Lata", "precio": 2500, "stock_inicial": 100}, {"nombre": "Agua Mineral 1.5L", "precio": 3200, "stock_inicial": 80}, {"nombre": "Agua Saborizada 1.5L", "precio": 3200, "stock_inicial": 70}]
}

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect() # Crear instancia

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Configuración
    # ¡IMPORTANTE! Cambia esta SECRET_KEY por una cadena larga, aleatoria y única en producción.
    # Puedes generar una con: python -c "import os; print(os.urandom(24).hex())"
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'c2a7b83c1e0f4d5a8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b') 
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(app.instance_path, 'bar_app.db')}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True # Poner en False para producción

    # Opcional: Clave separada para CSRF, aunque SECRET_KEY se usa por defecto si esta no está.
    app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY', 'una-clave-diferente-para-csrf-si-lo-deseas-abcdef123456')

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    db.init_app(app)
    migrate.init_app(app, db) 
    login_manager.init_app(app)
    csrf.init_app(app) # Inicializar CSRFProtect con la app
    
    login_manager.login_view = 'auth.login' 
    login_manager.login_message_category = 'info'
    login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."

    from .models import User, Product, Table 

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    

    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from .routes_admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    from .routes_mozo import mozo_bp
    app.register_blueprint(mozo_bp, url_prefix='/mozo')

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'mozo':
                return redirect(url_for('mozo.tables_view'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        try:
            if db.engine.dialect.has_table(db.engine.connect(), User.__tablename__):
                if User.query.count() == 0:
                    # ... (código de sembrado de usuarios)
                    users_data = [{"username": "admin1", "password": "password", "role": "admin"}, {"username": "admin2", "password": "password", "role": "admin"}, {"username": "mozo1", "password": "password", "role": "mozo"}, {"username": "mozo2", "password": "password", "role": "mozo"}, {"username": "mozo3", "password": "password", "role": "mozo"}]
                    for user_data in users_data:
                        hashed_password = generate_password_hash(user_data["password"])
                        new_user = User(username=user_data["username"], password_hash=hashed_password, role=user_data["role"])
                        db.session.add(new_user)
                    db.session.commit(); print("Usuarios iniciales sembrados.")
            else: print(f"Advertencia: Tabla '{User.__tablename__}' no existe. Ejecuta 'flask db upgrade'.")
            if db.engine.dialect.has_table(db.engine.connect(), Table.__tablename__):
                if Table.query.count() == 0:
                    for i in range(1, 11): table = Table(number=i, capacity=4, status='Vacía'); db.session.add(table)
                    db.session.commit(); print("Mesas iniciales sembradas.")
            else: print(f"Advertencia: Tabla '{Table.__tablename__}' no existe. Ejecuta 'flask db upgrade'.")
            if db.engine.dialect.has_table(db.engine.connect(), Product.__tablename__):
                if Product.query.count() == 0:
                    for category_name, products_in_category in INITIAL_MENU_PRODUCTS.items():
                        for prod_data in products_in_category:
                            product = Product(name=prod_data["nombre"], price=prod_data["precio"], type=category_name, stock=prod_data.get("stock_inicial", 50))
                            db.session.add(product)
                    db.session.commit(); print("Productos iniciales sembrados.")
            else: print(f"Advertencia: Tabla '{Product.__tablename__}' no existe. Ejecuta 'flask db upgrade'.")
        except Exception as e:
            print(f"Error durante sembrado/comprobación de tablas: {e}. Asegúrate de ejecutar 'flask db upgrade'.")
            
    return app