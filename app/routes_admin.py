from flask import Blueprint, render_template, request, redirect, url_for, flash, get_flashed_messages
from .models import Product, Order, OrderItem, Table, User
from . import db
from .utils import admin_required
from datetime import datetime
from collections import OrderedDict
from werkzeug.security import generate_password_hash
from sqlalchemy import func, select, literal_column
from sqlalchemy.orm import selectinload
from flask_login import current_user
from flask_wtf.csrf import generate_csrf  # <-- IMPORTACIÓN CLAVE

ITEMS_PER_PAGE = 10

admin_bp = Blueprint('admin', __name__)

def get_distinct_categories():
    """Obtiene una lista de todas las categorías de productos distintas, ordenadas."""
    try:
        from app import INITIAL_MENU_PRODUCTS
        preferred_categories = list(INITIAL_MENU_PRODUCTS.keys())
        
        db_categories_query = db.session.query(Product.type).distinct().order_by(Product.type).all()
        db_categories = [category[0] for category in db_categories_query if category[0]]
        
        final_categories = []
        for cat in preferred_categories:
            if cat in db_categories and cat not in final_categories:
                final_categories.append(cat)
        for cat in db_categories:
            if cat not in final_categories:
                final_categories.append(cat)
        
        if not final_categories and db_categories:
              return sorted(list(set(db_categories)))
        return final_categories
    except ImportError:
        categories_query = db.session.query(Product.type).distinct().order_by(Product.type).all()
        return [category[0] for category in categories_query if category[0]]


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html', title="Panel de Administrador")

# --- Product CRUD ---
@admin_bp.route('/products')
@admin_required
def list_products():
    page = request.args.get('page', 1, type=int)
    search_name = request.args.get('search_name', '').strip()
    search_category = request.args.get('search_category', '').strip()
    query = Product.query
    if search_name:
        query = query.filter(Product.name.ilike(f'%{search_name}%'))
    if search_category:
        query = query.filter(Product.type == search_category)
    pagination = query.order_by(Product.type, Product.name).paginate(
        page=page, per_page=ITEMS_PER_PAGE, error_out=False
    )
    products_on_page = pagination.items
    products_by_category = OrderedDict()
    distinct_categories_for_filter = get_distinct_categories()
    if products_on_page:
        current_categories_order = []
        if search_category and any(p.type == search_category for p in products_on_page):
            current_categories_order.append(search_category)
        for product in products_on_page:
            if product.type not in current_categories_order:
                current_categories_order.append(product.type)
        if not current_categories_order and not search_category:
              current_categories_order = distinct_categories_for_filter
        for category_name in current_categories_order:
            category_products = [p for p in products_on_page if p.type == category_name]
            if category_products:
                products_by_category[category_name] = category_products
        if search_category and not products_by_category.get(search_category):
            products_by_category.clear()
    
    # ** AÑADIR TOKEN **
    csrf_token_value = generate_csrf()
    
    return render_template(
        'admin/products.html',
        products_by_category=products_by_category,
        title="Gestionar Productos",
        distinct_categories_for_filter=distinct_categories_for_filter,
        search_name_value=search_name,
        search_category_value=search_category,
        pagination=pagination,
        csrf_token_value=csrf_token_value  # ** Pasar token a la plantilla **
    )

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    categories = get_distinct_categories()
    form_data = {}
    errors = {}
    form_action = url_for('admin.add_product')
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price', '')
        product_type_selected = request.form.get('type', '')
        new_category_input = request.form.get('new_category', '').strip()
        stock_str = request.form.get('stock', '')
        form_data = {'name': name, 'price': price_str, 'type': product_type_selected, 'new_category': new_category_input, 'stock': stock_str}
        final_product_type = product_type_selected
        if product_type_selected == 'Otro':
            if new_category_input:
                final_product_type = new_category_input
            else: errors['new_category'] = 'Debe especificar la nueva categoría si selecciona "Otra".'
        if not name: errors['name'] = 'El nombre es obligatorio.'
        if not price_str: errors['price'] = 'El precio es obligatorio.'
        if not final_product_type and not errors.get('new_category'): errors['type'] = 'La categoría es obligatoria.'
        if not stock_str: errors['stock'] = 'El stock es obligatorio.'
        if not errors:
            try:
                price = float(price_str)
                stock = int(stock_str)
                if price < 0: errors['price'] = 'El precio debe ser un número positivo.'
                if stock < 0: errors['stock'] = 'El stock debe ser un número entero positivo o cero.'
                if Product.query.filter_by(name=name).first(): errors['name'] = 'Este nombre de producto ya existe.'
                if not final_product_type and not errors.get('type'): errors['type'] = 'La categoría no puede estar vacía.'
                if not errors:
                    new_product = Product(name=name, price=price, type=final_product_type, stock=stock)
                    db.session.add(new_product); db.session.commit()
                    flash(f'¡Producto "{name}" añadido con éxito a la categoría "{final_product_type}"!', 'success')
                    return redirect(url_for('admin.list_products'))
            except ValueError:
                if not errors.get('price') and not price_str.replace('.', '', 1).isdigit(): errors['price'] = 'El precio debe ser un número válido.'
                if not errors.get('stock') and not stock_str.isdigit(): errors['stock'] = 'El stock debe ser un número entero válido.'
        if errors: flash('Por favor, corrige los errores en el formulario.', 'danger')
        
        # ** AÑADIR TOKEN (en caso de error POST) **
        csrf_token_value = generate_csrf()
        return render_template('admin/product_form.html', action="Añadir", product=form_data, title="Añadir Producto", categories=categories, form_action=form_action, errors=errors, csrf_token_value=csrf_token_value)
    
    # ** AÑADIR TOKEN (para la carga inicial GET) **
    csrf_token_value = generate_csrf()
    return render_template('admin/product_form.html', action="Añadir", product=form_data, title="Añadir Producto", categories=categories, form_action=form_action, errors=errors, csrf_token_value=csrf_token_value)

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product_to_edit = Product.query.get_or_404(product_id)
    categories = get_distinct_categories()
    form_action = url_for('admin.edit_product', product_id=product_id)
    errors = {}
    product_data_for_form = {
        'id': product_to_edit.id, 'name': product_to_edit.name, 'price': str(product_to_edit.price),
        'type': product_to_edit.type, 'new_category': '', 'stock': str(product_to_edit.stock)
    }
    if request.method == 'POST':
        original_name = product_to_edit.name
        product_data_for_form['name'] = request.form.get('name', '').strip()
        product_data_for_form['price'] = request.form.get('price', '')
        product_type_selected = request.form.get('type', '')
        product_data_for_form['new_category'] = request.form.get('new_category', '').strip()
        product_data_for_form['stock'] = request.form.get('stock', '')
        product_data_for_form['type'] = product_type_selected
        final_product_type = product_type_selected
        if product_type_selected == 'Otro':
            if product_data_for_form['new_category']:
                final_product_type = product_data_for_form['new_category']
            else: errors['new_category'] = 'Debe especificar la nueva categoría si selecciona "Otra".'
        if not product_data_for_form['name']: errors['name'] = 'El nombre es obligatorio.'
        if not product_data_for_form['price']: errors['price'] = 'El precio es obligatorio.'
        if not final_product_type and not errors.get('new_category'): errors['type'] = 'La categoría es obligatoria.'
        if not product_data_for_form['stock']: errors['stock'] = 'El stock es obligatorio.'
        if not errors:
            try:
                price_val = float(product_data_for_form['price'])
                stock_val = int(product_data_for_form['stock'])
                if price_val < 0: errors['price'] = 'El precio debe ser un número positivo.'
                if stock_val < 0: errors['stock'] = 'El stock debe ser un número entero positivo o cero.'
                existing_product_with_name = Product.query.filter(Product.name == product_data_for_form['name'], Product.id != product_id).first()
                if existing_product_with_name: errors['name'] = f'El nombre "{product_data_for_form["name"]}" ya está en uso.'
                if not final_product_type and not errors.get('type'): errors['type'] = 'La categoría no puede estar vacía.'
                if not errors:
                    product_to_edit.name = product_data_for_form['name']
                    product_to_edit.price = price_val
                    product_to_edit.type = final_product_type
                    product_to_edit.stock = stock_val
                    db.session.commit()
                    flash(f'¡Producto "{product_to_edit.name}" actualizado con éxito!', 'success')
                    return redirect(url_for('admin.list_products'))
            except ValueError:
                if not errors.get('price') and not product_data_for_form['price'].replace('.', '', 1).isdigit(): errors['price'] = 'El precio debe ser un número válido.'
                if not errors.get('stock') and not product_data_for_form['stock'].isdigit(): errors['stock'] = 'El stock debe ser un número entero válido.'
        if errors: flash('Por favor, corrige los errores en el formulario.', 'danger')
        
        # ** AÑADIR TOKEN (en caso de error POST) **
        csrf_token_value = generate_csrf()
        return render_template('admin/product_form.html', action="Editar", product=product_data_for_form, title=f"Editar {original_name}", categories=categories, form_action=form_action, errors=errors, csrf_token_value=csrf_token_value)
    
    # ** AÑADIR TOKEN (para la carga inicial GET) **
    csrf_token_value = generate_csrf()
    return render_template('admin/product_form.html', action="Editar", product=product_data_for_form, title=f"Editar {product_to_edit.name}", categories=categories, form_action=form_action, errors=errors, csrf_token_value=csrf_token_value)

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if OrderItem.query.filter_by(product_id=product.id).first():
        flash(f'El producto "{product.name}" no se puede eliminar ya que forma parte de pedidos existentes.', 'danger')
        return redirect(url_for('admin.list_products'))
    db.session.delete(product)
    db.session.commit()
    flash(f'¡Producto "{product.name}" eliminado con éxito!', 'success')
    return redirect(url_for('admin.list_products'))

# --- Sales Log ---
@admin_bp.route('/sales', methods=['GET'])
@admin_required
def sales_log():
    page = request.args.get('page', 1, type=int)
    date_filter_str = request.args.get('date', '').strip()
    sales_query = Order.query.filter(Order.status.in_(['Pagado', 'Venta Anulada']))
    date_filter = None
    if date_filter_str:
        try:
            date_filter = datetime.strptime(date_filter_str, '%Y-%m-%d').date()
            start_datetime = datetime.combine(date_filter, datetime.min.time())
            end_datetime = datetime.combine(date_filter, datetime.max.time())
            sales_query = sales_query.filter(Order.updated_at >= start_datetime, Order.updated_at <= end_datetime)
        except ValueError:
            flash("Formato de fecha inválido. Mostrando todos los registros.", "warning")
            date_filter_str = ""
    pagination = sales_query.order_by(Order.updated_at.desc()).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    sales_orders_on_page = pagination.items
    total_active_sales_value_query = Order.query.with_entities(func.sum(Order.total_amount)).filter_by(status='Pagado')
    if date_filter_str and date_filter:
        start_dt_total = datetime.combine(date_filter, datetime.min.time())
        end_dt_total = datetime.combine(date_filter, datetime.max.time())
        total_active_sales_value_query = total_active_sales_value_query.filter(Order.updated_at >= start_dt_total, Order.updated_at <= end_dt_total)
    total_active_sales_value = total_active_sales_value_query.scalar() or 0.0
    
    # ** AÑADIR TOKEN **
    csrf_token_value = generate_csrf()
    
    return render_template('admin/sales_log.html', sales_orders=sales_orders_on_page, total_active_sales_value=total_active_sales_value, date_filter=date_filter_str, title="Registro de Ventas", pagination=pagination, csrf_token_value=csrf_token_value)

@admin_bp.route('/sale_detail/<int:order_id>')
@admin_required
def sale_detail_view(order_id):
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    sale_order = Order.query.filter(Order.id == order_id, Order.status.in_(['Pagado', 'Venta Anulada'])) \
                             .options(selectinload(Order.items).selectinload(OrderItem.product),
                                      selectinload(Order.table_assigned)) \
                             .first_or_404()
    return render_template('admin/sale_detail.html', sale_order=sale_order, title=f"Detalle Venta Pedido #{sale_order.id}", return_page=page, return_date_filter=date_filter)

@admin_bp.route('/sales/annul/<int:order_id>', methods=['POST'])
@admin_required
def annul_sale(order_id):
    order_to_annul = Order.query.get_or_404(order_id)
    page = request.form.get('page', 1, type=int)
    date_filter = request.form.get('date', '')
    if order_to_annul.status != 'Pagado':
        flash('Solo se pueden anular ventas que fueron marcadas como "Pagado".', 'warning')
        return redirect(url_for('admin.sales_log', page=page, date=date_filter))
    stock_returned_messages = []
    for item in order_to_annul.items:
        if item.product:
            item.product.stock += item.quantity
            stock_returned_messages.append(f"{item.quantity}x {item.product.name}")
    order_to_annul.status = 'Venta Anulada'
    order_to_annul.updated_at = datetime.utcnow()
    if order_to_annul.type == 'mesa' and order_to_annul.table_assigned:
        if order_to_annul.table_assigned.status == 'Pendiente Pago':
            other_paid_orders_for_table = Order.query.filter(Order.table_id == order_to_annul.table_id, Order.status == 'Pagado', Order.id != order_to_annul.id).count()
            if other_paid_orders_for_table == 0:
                order_to_annul.table_assigned.status = 'Vacía'
    db.session.commit()
    if stock_returned_messages:
        flash(f'Venta (Pedido ID: {order_id}) anulada. Stock devuelto para: {", ".join(stock_returned_messages)}.', 'success')
    else:
        flash(f'Venta (Pedido ID: {order_id}) anulada.', 'success')
    return redirect(url_for('admin.sales_log', page=page, date=date_filter))

# --- Gestión de Mesas (Admin) ---
@admin_bp.route('/manage_tables', methods=['GET'])
@admin_required
def manage_tables_view():
    page = request.args.get('page', 1, type=int)
    pagination = Table.query.order_by(Table.number).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    tables_on_page = pagination.items
    add_form_action = url_for('admin.add_table_action', page=page)
    form_data_add = {'number': request.args.get('number_val_add', ''), 'capacity': request.args.get('capacity_val_add', '')}
    errors_add = {k.replace('_err_msg',''):v for k,v in request.args.items() if k.endswith('_add_err_msg')}
    if 'add_error' in request.args: # Re-check mandatory fields if error signal exists
        if not form_data_add['number'] and 'number_add' not in errors_add : errors_add['number_add'] = "Número obligatorio."
        if not form_data_add['capacity'] and 'capacity_add' not in errors_add: errors_add['capacity_add'] = "Capacidad obligatoria."
    edit_table_id_param = request.args.get('edit_table_id', None, type=int)
    table_to_edit_obj = None; form_data_edit = {}; edit_form_action_url = None; errors_edit = {}
    if edit_table_id_param:
        table_to_edit_obj = Table.query.get(edit_table_id_param)
        if table_to_edit_obj:
            edit_form_action_url = url_for('admin.edit_table_action', table_id=edit_table_id_param, page=page)
            form_data_edit = {'number': request.args.get(f'number_val_edit', str(table_to_edit_obj.number)), 'capacity': request.args.get(f'capacity_val_edit', str(table_to_edit_obj.capacity))}
            if request.args.get(f'edit_error_{edit_table_id_param}'):
                  for key,value in request.args.items():
                      if key.startswith(f'number_edit_err_msg_{edit_table_id_param}'): errors_edit['number_edit'] = value
                      if key.startswith(f'capacity_edit_err_msg_{edit_table_id_param}'): errors_edit['capacity_edit'] = value
                      if key.startswith(f'general_edit_err_msg_{edit_table_id_param}'): errors_edit['general_edit'] = value
    
    # ** AÑADIR TOKEN **
    csrf_token_value = generate_csrf()
    
    return render_template('admin/manage_tables.html', tables_on_page=tables_on_page, title="Gestionar Mesas", form_data_add=form_data_add, add_form_action=add_form_action, errors_add=errors_add, pagination=pagination, show_edit_form_for_id=edit_table_id_param, table_to_edit_obj=table_to_edit_obj, form_data_edit=form_data_edit, edit_form_action=edit_form_action_url, errors_edit=errors_edit, csrf_token_value=csrf_token_value)

@admin_bp.route('/manage_tables/add_action', methods=['POST'])
@admin_required
def add_table_action():
    number_str = request.form.get('number'); capacity_str = request.form.get('capacity')
    page = request.form.get('page', 1, type=int)
    redirect_args = {'add_error': 'True', 'number_val_add': number_str or '', 'capacity_val_add': capacity_str or '', 'page': page}
    has_errors = False
    if not number_str: redirect_args['number_add_err_msg'] = "El número es obligatorio."; has_errors = True
    if not capacity_str: redirect_args['capacity_add_err_msg'] = "La capacidad es obligatoria."; has_errors = True
    if has_errors: flash('Error al añadir mesa. Revisa los campos.', 'danger'); return redirect(url_for('admin.manage_tables_view', **redirect_args))
    try:
        number = int(number_str); capacity = int(capacity_str)
        if capacity <= 0 or number <= 0: flash('El número de mesa y la capacidad deben ser positivos.', 'warning'); redirect_args['general_add_err_msg'] = 'Valores deben ser positivos.'
        elif Table.query.filter_by(number=number).first(): flash(f'La mesa número {number} ya existe.', 'warning'); redirect_args['number_add_err_msg'] = f'Mesa {number} ya existe.'
        else:
            new_table = Table(number=number, capacity=capacity, status='Vacía'); db.session.add(new_table); db.session.commit()
            flash(f'Mesa {number} añadida con éxito.', 'success'); return redirect(url_for('admin.manage_tables_view', page=page))
    except ValueError: flash('Número de mesa o capacidad inválidos.', 'danger'); redirect_args['general_add_err_msg'] = 'Número o capacidad inválidos.'
    return redirect(url_for('admin.manage_tables_view', **redirect_args))

@admin_bp.route('/manage_tables/edit_form_prep/<int:table_id>', methods=['GET'])
@admin_required
def edit_table_form_prep(table_id):
    page = request.args.get('page', 1, type=int)
    return redirect(url_for('admin.manage_tables_view', edit_table_id=table_id, page=page))

@admin_bp.route('/manage_tables/edit_action/<int:table_id>', methods=['POST'])
@admin_required
def edit_table_action(table_id):
    table_to_edit = Table.query.get_or_404(table_id)
    new_number_str = request.form.get('number'); new_capacity_str = request.form.get('capacity')
    page = request.form.get('page', 1, type=int)
    redirect_args = {'edit_table_id': str(table_id), f'edit_error_{table_id}': 'True', 'number_val_edit': new_number_str or '', 'capacity_val_edit': new_capacity_str or '', 'page': page }
    has_errors = False
    if not new_number_str: redirect_args[f'number_edit_err_msg_{table_id}'] = 'El número es obligatorio.'; has_errors = True
    if not new_capacity_str: redirect_args[f'capacity_edit_err_msg_{table_id}'] = 'La capacidad es obligatoria.'; has_errors = True
    if has_errors: flash('Error al editar mesa. Revisa los campos.', 'danger'); return redirect(url_for('admin.manage_tables_view', **redirect_args))
    try:
        new_number = int(new_number_str); new_capacity = int(new_capacity_str)
        if new_capacity <= 0 or new_number <= 0: flash('El número de mesa y la capacidad deben ser positivos.', 'warning'); redirect_args[f'general_edit_err_msg_{table_id}'] = 'Valores deben ser positivos.'
        else:
            existing_table = Table.query.filter(Table.number == new_number, Table.id != table_id).first()
            if existing_table: flash(f'El número de mesa {new_number} ya está en uso por otra mesa.', 'warning'); redirect_args[f'number_edit_err_msg_{table_id}'] = f'Número {new_number} ya en uso.'
            else:
                table_to_edit.number = new_number; table_to_edit.capacity = new_capacity
                db.session.commit(); flash(f'Mesa {table_to_edit.number} actualizada con éxito.', 'success')
                return redirect(url_for('admin.manage_tables_view', page=page))
    except ValueError: flash('Número de mesa o capacidad inválidos.', 'danger'); redirect_args[f'general_edit_err_msg_{table_id}'] = 'Número o capacidad inválidos.'
    return redirect(url_for('admin.manage_tables_view', **redirect_args))

@admin_bp.route('/manage_tables/delete/<int:table_id>', methods=['POST'])
@admin_required
def delete_table(table_id):
    table = Table.query.get_or_404(table_id)
    page = request.form.get('page', 1, type=int)
    if Order.query.filter_by(table_id=table.id).first():
        flash(f'La mesa {table.number} no se puede eliminar porque tiene pedidos asociados.', 'danger')
    elif table.status != 'Vacía':
        flash(f'La mesa {table.number} debe estar "Vacía" para ser eliminada.', 'danger')
    else:
        db.session.delete(table); db.session.commit()
        flash(f'Mesa {table.number} eliminada con éxito.', 'success')
    return redirect(url_for('admin.manage_tables_view', page=page))

# --- Gestión de Usuarios (Admin) ---
@admin_bp.route('/users')
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    pagination = User.query.order_by(User.id).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
    users_on_page = pagination.items
    
    # ** AÑADIR TOKEN **
    csrf_token_value = generate_csrf()
    
    return render_template('admin/manage_users.html', users=users_on_page, title="Gestionar Usuarios", pagination=pagination, csrf_token_value=csrf_token_value)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    form_action = url_for('admin.add_user'); user_data = {}; errors = {}
    if request.method == 'POST':
        username = request.form.get('username', '').strip(); password = request.form.get('password', ''); role = request.form.get('role', '')
        user_data = {'username': username, 'role': role}
        if not username: errors['username'] = 'El nombre de usuario es obligatorio.'
        if not password: errors['password'] = 'La contraseña es obligatoria.'
        if not role: errors['role'] = 'El rol es obligatorio.'
        if password and len(password) < 6: errors['password'] = 'La contraseña debe tener al menos 6 caracteres.'
        if username and User.query.filter_by(username=username).first(): errors['username'] = 'Ese nombre de usuario ya existe.'
        if role and role not in ['admin', 'mozo']: errors['role'] = 'Rol inválido seleccionado.'
        if not errors:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password, role=role)
            db.session.add(new_user); db.session.commit()
            flash(f'Usuario "{username}" creado con éxito.', 'success'); return redirect(url_for('admin.manage_users'))
        else: flash('Por favor, corrige los errores en el formulario.', 'danger')
        
        # ** AÑADIR TOKEN (en caso de error POST) **
        csrf_token_value = generate_csrf()
        return render_template('admin/user_form.html', action="Añadir", form_action=form_action, user=user_data, title="Añadir Usuario", errors=errors, csrf_token_value=csrf_token_value)
    
    # ** AÑADIR TOKEN (para la carga inicial GET) **
    csrf_token_value = generate_csrf()
    return render_template('admin/user_form.html', action="Añadir", form_action=form_action, user=user_data, title="Añadir Usuario", errors=errors, csrf_token_value=csrf_token_value)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id); form_action = url_for('admin.edit_user', user_id=user_id); errors = {}
    user_data_for_template = {'username': user_to_edit.username, 'role': user_to_edit.role}
    if request.method == 'POST':
        password = request.form.get('password'); role_from_form = request.form.get('role')
        user_data_for_template['role'] = role_from_form
        form_had_errors = False
        if role_from_form not in ['admin', 'mozo']: errors['role'] = 'Rol inválido seleccionado.'; form_had_errors = True
        else:
            can_change_role = True
            if user_to_edit.role == 'admin' and role_from_form == 'mozo':
                admin_count = User.query.filter_by(role='admin').count()
                if admin_count <= 1: errors['role'] = 'No se puede cambiar el rol del único administrador.'; form_had_errors = True; can_change_role = False
            if can_change_role: user_to_edit.role = role_from_form
            password_changed_successfully = False
            if password:
                if len(password) < 6: errors['password'] = 'La nueva contraseña debe tener al menos 6 caracteres.'; form_had_errors = True
                else: user_to_edit.password_hash = generate_password_hash(password); password_changed_successfully = True
            if not form_had_errors and not errors:
                try:
                    db.session.commit(); flash_message = f'Usuario "{user_to_edit.username}" actualizado.'
                    if password_changed_successfully: flash_message += ' Contraseña cambiada.'
                    flash(flash_message, 'success'); return redirect(url_for('admin.manage_users'))
                except Exception as e: db.session.rollback(); flash(f'Error al actualizar el usuario: {str(e)}', 'danger')
        if errors: flash('Por favor, corrige los errores en el formulario.', 'danger')
        
        # ** AÑADIR TOKEN (en caso de error POST) **
        csrf_token_value = generate_csrf()
        return render_template('admin/user_form.html', action="Editar", form_action=form_action, user=user_data_for_template, title=f"Editar Usuario {user_to_edit.username}", errors=errors, csrf_token_value=csrf_token_value)
    
    # ** AÑADIR TOKEN (para la carga inicial GET) **
    csrf_token_value = generate_csrf()
    return render_template('admin/user_form.html', action="Editar", form_action=form_action, user=user_data_for_template, title=f"Editar Usuario {user_to_edit.username}", errors=errors, csrf_token_value=csrf_token_value)


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    page = request.form.get('page', 1, type=int)
    if user_to_delete.id == current_user.id: flash('No puedes eliminar tu propia cuenta.', 'danger'); return redirect(url_for('admin.manage_users', page=page))
    if user_to_delete.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1: flash('No se puede eliminar el único administrador.', 'danger'); return redirect(url_for('admin.manage_users', page=page))
    db.session.delete(user_to_delete); db.session.commit()
    flash(f'Usuario "{user_to_delete.username}" eliminado con éxito.', 'success')
    return redirect(url_for('admin.manage_users', page=page))