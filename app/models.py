from datetime import datetime
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# --- Modelos User, Product, Table (Sin cambios) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='mozo')

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

# --- Modelo Order (CON LA CORRECCIÓN IMPORTANTE) ---
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

    # ========= ESTA FUNCIÓN ES LA CLAVE DE LA SOLUCIÓN =========
    def calculate_total(self):
        """
        Calcula y actualiza el monto total del pedido sumando correctamente
        los subtotales de TODOS sus ítems.
        """
        total_calculado = sum(item.subtotal for item in self.items if item.subtotal is not None)
        self.total_amount = total_calculado
    # ===============================================================

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
        """Calcula el subtotal para este ítem específico."""
        self.subtotal = self.quantity * self.unit_price