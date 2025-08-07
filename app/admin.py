from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import Product, Order, OrderItem, Table, User 
from . import db
from .utils import admin_required
from datetime import datetime
from collections import OrderedDict
from werkzeug.security import generate_password_hash
from sqlalchemy import func 
from flask_login import current_user
from flask_wtf.csrf import generate_csrf

# CORRECCIÓN: Se elimina template_folder='templates'
admin_bp = Blueprint('admin', __name__)

ITEMS_PER_PAGE = 10

def get_distinct_categories():
    try:
        from app import INITIAL_MENU_PRODUCTS 
        preferred_categories = list(INITIAL_MENU_PRODUCTS.keys())
        db_categories_query = db.session.query(Product.type).distinct().order_by(Product.type).all()
        db_categories = [category[0] for category in db_categories_query if category[0]] 
        final_categories = []
        for cat in preferred_categories:
            if cat in db_categories and cat not in final_categories: final_categories.append(cat)
        for cat in db_categories:
            if cat not in final_categories: final_categories.append(cat)
        return final_categories if final_categories else sorted(list(set(db_categories)))
    except (ImportError, AttributeError): 
        return [c[0] for c in db.session.query(Product.type).distinct().order_by(Product.type).all() if c[0]]

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html', title="Panel de Administrador")

# --- Product CRUD ---
@admin_bp.route('/products')
@admin_required
def list_products():
    page = request.args.get('page', 1, type=int)
    pagination = Product.query.order_by(Product.type, Product.name).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    products_on_page = pagination.items
    csrf_token_value = generate_csrf()
    return render_template('admin/products.html', products=products_on_page, title="Gestionar Productos", pagination=pagination, csrf_token_value=csrf_token_value)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price')
        product_type = request.form.get('type')
        stock_str = request.form.get('stock')
        
        if not all([name, price_str, product_type, stock_str]):
            flash('Todos los campos son obligatorios.', 'danger')
        else:
            try:
                price = float(price_str)
                stock = int(stock_str)
                new_product = Product(name=name, price=price, type=product_type, stock=stock)
                db.session.add(new_product)
                db.session.commit()
                flash('Producto añadido con éxito.', 'success')
                return redirect(url_for('admin.list_products'))
            except ValueError:
                flash('El precio y el stock deben ser números válidos.', 'danger')

    csrf_token_value = generate_csrf()
    return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=get_distinct_categories(), form_action=url_for('admin.add_product'), csrf_token_value=csrf_token_value)

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        product.price = float(request.form.get('price'))
        product.type = request.form.get('type')
        product.stock = int(request.form.get('stock'))
        db.session.commit()
        flash('Producto actualizado con éxito.', 'success')
        return redirect(url_for('admin.list_products'))
    
    csrf_token_value = generate_csrf()
    return render_template('admin/product_form.html', action="Editar", product=product, title=f"Editar {product.name}", categories=get_distinct_categories(), form_action=url_for('admin.edit_product', product_id=product.id), csrf_token_value=csrf_token_value)

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Producto eliminado con éxito.', 'success')
    return redirect(url_for('admin.list_products'))

# --- Sales Log ---
@admin_bp.route('/sales')
@admin_required
def sales_log():
    page = request.args.get('page', 1, type=int)
    sales = Order.query.filter(Order.status.in_(['Pagado', 'Venta Anulada'])).order_by(Order.updated_at.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    csrf_token_value = generate_csrf()
    return render_template('admin/sales_log.html', sales_orders=sales.items, pagination=sales, title="Registro de Ventas", csrf_token_value=csrf_token_value)

# --- Table Management ---
@admin_bp.route('/manage_tables')
@admin_required
def manage_tables_view():
    page = request.args.get('page', 1, type=int)
    pagination = Table.query.order_by(Table.number).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    csrf_token_value = generate_csrf()
    return render_template('admin/manage_tables.html', tables_on_page=pagination.items, pagination=pagination, title="Gestionar Mesas", csrf_token_value=csrf_token_value)

# --- User Management ---
@admin_bp.route('/users')
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    pagination = User.query.order_by(User.id).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    csrf_token_value = generate_csrf()
    return render_template('admin/manage_users.html', users=pagination.items, title="Gestionar Usuarios", pagination=pagination, csrf_token_value=csrf_token_value)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        role = request.form.get('role')
        if not all([username, password, role]):
            flash('Todos los campos son obligatorios.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'danger')
        else:
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Usuario añadido con éxito.', 'success')
            return redirect(url_for('admin.manage_users'))
    
    csrf_token_value = generate_csrf()
    return render_template('admin/user_form.html', action="Añadir", title="Añadir Usuario", form_action=url_for('admin.add_user'), csrf_token_value=csrf_token_value)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        password = request.form.get('password')
        role = request.form.get('role')
        user.role = role
        if password:
            user.set_password(password)
        db.session.commit()
        flash(f'Usuario {user.username} actualizado con éxito.', 'success')
        return redirect(url_for('admin.manage_users'))

    csrf_token_value = generate_csrf()
    return render_template('admin/user_form.html', action="Editar", user=user, title=f"Editar Usuario {user.username}", form_action=url_for('admin.edit_user', user_id=user.id), csrf_token_value=csrf_token_value)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('No se puede eliminar al único administrador.', 'danger')
            return redirect(url_for('admin.manage_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.username} eliminado con éxito.', 'success')
    return redirect(url_for('admin.manage_users'))
