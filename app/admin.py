# Archivo: app/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .models import Product, Order, OrderItem, Table, User
from . import db
from .utils import admin_required
from datetime import datetime, date
from collections import OrderedDict
from sqlalchemy import func
from flask_login import current_user

admin_bp = Blueprint('admin', __name__)

ITEMS_PER_PAGE = 10

def get_distinct_categories():
    db_categories_query = db.session.query(Product.type).distinct().order_by(Product.type).all()
    db_categories = [category[0] for category in db_categories_query if category[0]]
    return sorted(list(set(db_categories)))

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = date.today()
    
    # Ventas del día
    total_sales_today = db.session.query(func.sum(Order.total_amount))\
        .filter(db.func.date(Order.updated_at) == today, Order.status == 'Pagado').scalar() or 0.0

    # Desglose de ventas del día
    sales_today_table = db.session.query(func.sum(Order.total_amount))\
        .filter(db.func.date(Order.updated_at) == today, Order.status == 'Pagado', Order.type == 'Mesa').scalar() or 0.0
    sales_today_takeaway = db.session.query(func.sum(Order.total_amount))\
        .filter(db.func.date(Order.updated_at) == today, Order.status == 'Pagado', Order.type == 'Para Llevar').scalar() or 0.0
    
    # Pedidos activos y mesas ocupadas
    active_orders_count = Order.query.filter(Order.status.in_(['Activo', 'Pendiente'])).count()
    tables_occupied_count = Table.query.filter(Table.status == 'Ocupada').count()
    
    # Top 5 productos más vendidos (histórico)
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_quantity')
    ).join(OrderItem).group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    return render_template('admin/dashboard.html', 
        title="Panel de Administrador",
        total_sales_today=total_sales_today,
        sales_today_table=sales_today_table,
        sales_today_takeaway=sales_today_takeaway,
        active_orders_count=active_orders_count,
        tables_occupied_count=tables_occupied_count,
        top_products=top_products
    )

@admin_bp.route('/products')
@admin_required
def products():
    page = request.args.get('page', 1, type=int)
    search_name = request.args.get('search_name', '').strip()
    search_category = request.args.get('search_category', '').strip()
    
    query = Product.query
    if search_name:
        query = query.filter(Product.name.ilike(f'%{search_name}%'))
    if search_category:
        query = query.filter(Product.type == search_category)

    pagination = query.order_by(Product.type, Product.name).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    
    products_on_page = pagination.items

    return render_template('admin/products.html', 
                           products_on_page=products_on_page, 
                           title="Gestionar Productos", 
                           pagination=pagination, 
                           search_name_value=search_name,
                           search_category_value=search_category,
                           distinct_categories_for_filter=get_distinct_categories())


@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    distinct_categories = get_distinct_categories()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price')
        product_type = request.form.get('type')
        stock_str = request.form.get('stock')
        new_category = request.form.get('new_category', '').strip()

        if product_type == 'Otro':
            if not new_category:
                flash('Debe especificar el nombre de la nueva categoría.', 'danger')
                return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=distinct_categories, product={'name': name, 'price': price_str, 'stock': stock_str})
            product_type = new_category

        try:
            price = float(price_str)
            stock = int(stock_str)
            new_product = Product(name=name, price=price, type=product_type, stock=stock)
            db.session.add(new_product)
            db.session.commit()
            flash('Producto añadido con éxito.', 'success')
            return redirect(url_for('admin.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al añadir el producto: {str(e)}', 'danger')

    return render_template('admin/product_form.html', action="Añadir", title="Añadir Producto", categories=distinct_categories)

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    distinct_categories = get_distinct_categories()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price')
        product_type = request.form.get('type')
        stock_str = request.form.get('stock')
        new_category = request.form.get('new_category', '').strip()

        if product_type == 'Otro':
            if not new_category:
                flash('Debe especificar el nombre de la nueva categoría.', 'danger')
                return render_template('admin/product_form.html', action="Editar", product=product, title=f"Editar {product.name}", categories=distinct_categories)
            product.type = new_category
        else:
            product.type = product_type
        
        try:
            product.name = name
            product.price = float(price_str)
            product.stock = int(stock_str)
            db.session.commit()
            flash('Producto actualizado con éxito.', 'success')
            return redirect(url_for('admin.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al editar el producto: {str(e)}', 'danger')
    
    return render_template('admin/product_form.html', action="Editar", product=product, title=f"Editar {product.name}", categories=distinct_categories)

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Producto eliminado con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el producto: {str(e)}', 'danger')
    return redirect(url_for('admin.products'))

@admin_bp.route('/sales')
@admin_required
def sales_log():
    page = request.args.get('page', 1, type=int)
    date_filter_str = request.args.get('date', '').strip()
    
    query = Order.query.filter(Order.status.in_(['Pagado', 'Venta Anulada']))
    
    date_filter = None
    if date_filter_str:
        try:
            date_filter = datetime.strptime(date_filter_str, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Order.updated_at) == date_filter)
        except ValueError:
            flash('Formato de fecha inválido. Mostrando todos los resultados.', 'warning')
            date_filter_str = ''

    pagination = query.order_by(Order.updated_at.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)

    # Base query for paid orders
    base_sales_query = db.session.query(func.sum(Order.total_amount)).filter(Order.status == 'Pagado')
    if date_filter:
        base_sales_query = base_sales_query.filter(db.func.date(Order.updated_at) == date_filter)

    # Calculate totals
    total_sales = base_sales_query.scalar() or 0.0
    total_sales_table = base_sales_query.filter(Order.type == 'Mesa').scalar() or 0.0
    total_sales_takeaway = base_sales_query.filter(Order.type == 'Para Llevar').scalar() or 0.0

    return render_template('admin/sales_log.html', 
                           pagination=pagination, 
                           title="Registro de Ventas", 
                           date_filter=date_filter_str,
                           total_sales=total_sales,
                           total_sales_table=total_sales_table,
                           total_sales_takeaway=total_sales_takeaway)


@admin_bp.route('/sale/detail/<int:order_id>')
@admin_required
def sale_detail_view(order_id):
    order = Order.query.get_or_404(order_id)
    return_page = request.args.get('page', 1, type=int)
    return_date_filter = request.args.get('date', '')
    
    return render_template('admin/sale_detail.html', 
                           sale_order=order, 
                           title=f"Detalle de Venta #{order.id}",
                           return_page=return_page,
                           return_date_filter=return_date_filter)

@admin_bp.route('/annul_sale/<int:order_id>', methods=['POST'])
@admin_required
def annul_sale(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'Pagado':
        order.status = 'Venta Anulada'
        order.updated_at = datetime.utcnow()
        for item in order.items:
            item.product.stock += item.quantity
        db.session.commit()
        flash(f'Venta #{order.id} anulada con éxito. El stock ha sido repuesto.', 'success')
    else:
        flash('Solo se pueden anular ventas con estado "Pagado".', 'danger')

    return_page = request.form.get('page', 1, type=int)
    return_date_filter = request.form.get('date', '')
    return redirect(url_for('admin.sales_log', page=return_page, date=return_date_filter))


@admin_bp.route('/tables')
@admin_required
def manage_tables():
    page = request.args.get('page', 1, type=int)
    pagination = Table.query.order_by(Table.number).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    
    return render_template('admin/manage_tables.html', 
                           tables_on_page=pagination.items, 
                           pagination=pagination, 
                           title="Gestionar Mesas")

@admin_bp.route('/tables/add', methods=['POST'])
@admin_required
def add_table():
    number_str = request.form.get('number')
    capacity_str = request.form.get('capacity')
    
    if not number_str or not capacity_str:
        flash('El número y la capacidad de la mesa son obligatorios.', 'danger')
        return redirect(url_for('admin.manage_tables'))
        
    number = int(number_str)
    capacity = int(capacity_str)

    if Table.query.filter_by(number=number).first():
        flash(f'Ya existe una mesa con el número {number}.', 'danger')
    else:
        new_table = Table(number=number, capacity=capacity, status='Vacía')
        db.session.add(new_table)
        db.session.commit()
        flash(f'Mesa {number} añadida con éxito.', 'success')
    
    return redirect(url_for('admin.manage_tables'))

@admin_bp.route('/tables/edit/<int:table_id>', methods=['POST'])
@admin_required
def edit_table(table_id):
    table = Table.query.get_or_404(table_id)
    page = request.form.get('page', 1, type=int)

    new_number = request.form.get('number', type=int)
    new_capacity = request.form.get('capacity', type=int)
    
    existing_table = Table.query.filter(Table.number == new_number, Table.id != table_id).first()
    if existing_table:
        flash(f'Ya existe otra mesa con el número {new_number}.', 'danger')
    else:
        table.number = new_number
        table.capacity = new_capacity
        db.session.commit()
        flash(f'Mesa {table.number} actualizada con éxito.', 'success')
    
    return redirect(url_for('admin.manage_tables', page=page))

@admin_bp.route('/tables/delete/<int:table_id>', methods=['POST'])
@admin_required
def delete_table(table_id):
    table = Table.query.get_or_404(table_id)
    if table.status != 'Vacía':
        flash('No se puede eliminar una mesa que está ocupada. Libérela primero.', 'danger')
    elif table.orders.first():
         flash('No se puede eliminar una mesa que tiene pedidos históricos asociados.', 'danger')
    else:
        db.session.delete(table)
        db.session.commit()
        flash(f'Mesa {table.number} eliminada con éxito.', 'success')
    
    page = request.form.get('page', 1, type=int)
    return redirect(url_for('admin.manage_tables', page=page))

@admin_bp.route('/users')
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    pagination = User.query.order_by(User.id).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    return render_template('admin/manage_users.html', users=pagination.items, title="Gestionar Usuarios", pagination=pagination)

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
    
    return render_template('admin/user_form.html', action="Añadir", title="Añadir Usuario")

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

    return render_template('admin/user_form.html', action="Editar", user=user, title=f"Editar Usuario {user.username}")

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('No se puede eliminar al único administrador del sistema.', 'danger')
            return redirect(url_for('admin.manage_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.username} eliminado con éxito.', 'success')
    return redirect(url_for('admin.manage_users'))