from datetime import datetime
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='mozo')

    # --- CORRECCIÓN CLAVE: AÑADIR ESTOS DOS MÉTODOS ---
    def set_password(self, password):
        """Crea un hash seguro para la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica el hash de la contraseña."""
        return check_password_hash(self.password_hash, password)
    # --- FIN DE LA CORRECCIÓN ---

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    stock = db.Column(db.Integer, default=0)

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Vacía')
    orders = db.relationship('Order', back_populates='table_assigned', lazy='dynamic')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pendiente')
    customer_name = db.Column(db.String(100), nullable=True)
    total_amount = db.Column(db.Float, nullable=True, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=True)
    table_assigned = db.relationship('Table', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade="all, delete-orphan")

    def calculate_total(self):
        total = sum(item.subtotal for item in self.items if item.subtotal is not None)
        self.total_amount = total

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product')

    def __init__(self, **kwargs):
        super(OrderItem, self).__init__(**kwargs)
        self.calculate_subtotal()

    def calculate_subtotal(self):
        self.subtotal = self.quantity * self.unit_price
