from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, get_flashed_messages
from .models import Table, Product, Order, OrderItem
from . import db
from .utils import mozo_required
from sqlalchemy.orm import joinedload, selectinload
from collections import OrderedDict
from datetime import datetime
from flask_wtf.csrf import generate_csrf

mozo_bp = Blueprint('mozo', __name__)

def get_products_by_category():
    products_query = Product.query.filter(Product.stock > 0).order_by(Product.type, Product.name).all()
    products_by_cat = OrderedDict()
    preferred_categories = [
        "Sandwiches", "Hamburguesas", "Pizzas", "Milanesas al Plato", "Tostados & Especiales", 
        "Papas Fritas", "Agregados", "Bebidas con Alcohol", "Bebidas sin Alcohol", "Postre", "Otro"
    ]
    for cat_name in preferred_categories:
        products_by_cat[cat_name] = []
    for product in products_query:
        if product.type not in products_by_cat:
            products_by_cat[product.type] = []
        products_by_cat[product.type].append(product)
    final_products_by_cat = OrderedDict()
    for cat_name, prods_in_cat in products_by_cat.items():
        if prods_in_cat:
            final_products_by_cat[cat_name] = prods_in_cat
    return final_products_by_cat

@mozo_bp.route('/tables')
@mozo_required
def tables_view():
    tables_query = Table.query.order_by(Table.number).all()
    return render_template('mozo/tables.html', tables_data=tables_query, title="Mesas del Restaurante")

@mozo_bp.route('/table/<int:table_id>')
@mozo_required
def table_detail_view(table_id):
    table_instance = Table.query.get_or_404(table_id)
    current_order = Order.query.filter_by(table_id=table_instance.id, status='Pendiente').first()
    products_by_category = get_products_by_category()
    csrf_token_value = generate_csrf()
    return render_template('mozo/table_detail.html', table=table_instance, current_order=current_order, products_by_category=products_by_category, title=f"Mesa {table_instance.number}", csrf_token_value=csrf_token_value)

@mozo_bp.route('/table/<int:table_id>/start_order', methods=['POST'])
@mozo_required
def start_table_order(table_id):
    table = Table.query.get_or_404(table_id)
    if table.status == 'Vacía':
        new_order = Order(type='mesa', table_id=table.id, status='Pendiente')
        db.session.add(new_order)
        table.status = 'Ocupada'
        db.session.commit()
        flash('Nuevo pedido iniciado.', 'success')
    else:
        flash('La mesa no está vacía.', 'warning')
    return redirect(url_for('mozo.table_detail_view', table_id=table.id))

@mozo_bp.route('/order/<int:order_id>/add_item', methods=['POST'])
@mozo_required
def add_item_to_order(order_id):
    order = Order.query.get_or_404(order_id)
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    product = Product.query.get_or_404(product_id)

    order_item = OrderItem.query.filter_by(order_id=order.id, product_id=product.id).first()
    if order_item:
        order_item.quantity += quantity
        order_item.calculate_subtotal()
    else:
        order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=quantity, unit_price=product.price)
        db.session.add(order_item)
    
    product.stock -= quantity
    
    # --- LA SOLUCIÓN DEFINITIVA ---
    # 1. Hacemos flush para enviar los cambios a la "sala de espera" de la BD.
    db.session.flush()
    # 2. Refrescamos el objeto 'order' para que su lista 'items' se actualice AHORA MISMO.
    db.session.refresh(order)
    # 3. AHORA SÍ, calculamos el total con la lista de ítems 100% actualizada.
    order.calculate_total()
    
    db.session.commit()
    
    return jsonify({
        'success': True, 'message': f'{product.name} añadido.', 'order_total': order.total_amount,
        'item': {
            'id': order_item.id, 'name': product.name, 'quantity': order_item.quantity,
            'unit_price': order_item.unit_price, 'subtotal': order_item.subtotal
        }
    })

@mozo_bp.route('/order_item/<int:item_id>/remove', methods=['POST'])
@mozo_required
def remove_item_from_order(item_id):
    order_item = OrderItem.query.get_or_404(item_id)
    order = order_item.order
    product = order_item.product

    if product:
        product.stock += order_item.quantity
    
    db.session.delete(order_item)

    # --- LA MISMA SOLUCIÓN AL QUITAR UN ÍTEM ---
    db.session.flush()
    db.session.refresh(order)
    order.calculate_total()

    db.session.commit()

    return jsonify({
        'success': True, 'message': 'Ítem eliminado.', 'order_total': order.total_amount
    })

# ... (El resto del código no cambia) ...

@mozo_bp.route('/order/<int:order_id>/mark_paid', methods=['POST'])
@mozo_required
def mark_order_paid(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'Pendiente' and order.items:
        order.status = 'Pagado'
        order.updated_at = datetime.utcnow()
        if order.table_assigned:
            order.table_assigned.status = 'Pendiente Pago'
        db.session.commit()
        flash(f'Pedido #{order.id} marcado como pagado.', 'success')
    else:
        flash('El pedido no se puede marcar como pagado.', 'warning')
    redirect_url = url_for('mozo.takeaway_orders_view') if order.type == 'llevar' else url_for('mozo.table_detail_view', table_id=order.table_id)
    return redirect(redirect_url)

@mozo_bp.route('/table/<int:table_id>/liberate', methods=['POST'])
@mozo_required
def liberate_table(table_id):
    table = Table.query.get_or_404(table_id)
    table.status = 'Vacía'
    db.session.commit()
    flash(f'Mesa {table.number} liberada.', 'success')
    return redirect(url_for('mozo.tables_view'))

@mozo_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@mozo_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'Pendiente':
        for item in order.items:
            if item.product:
                item.product.stock += item.quantity
        order.status = 'Cancelado'
        order.updated_at = datetime.utcnow()
        if order.table_assigned and order.table_assigned.status == 'Ocupada':
            order.table_assigned.status = 'Vacía'
        db.session.commit()
        flash(f'Pedido #{order.id} cancelado. Stock devuelto.', 'success')
    else:
        flash('Este pedido no se puede cancelar.', 'warning')
    redirect_url = url_for('mozo.takeaway_orders_view') if order.type == 'llevar' else url_for('mozo.table_detail_view', table_id=order.table_id)
    return redirect(redirect_url)

@mozo_bp.route('/takeaway')
@mozo_required
def takeaway_orders_view():
    orders = Order.query.filter_by(type='llevar').order_by(Order.created_at.desc()).all()
    for order in orders:
        if order.total_amount is None:
            order.calculate_total()
    csrf_token_value = generate_csrf()
    return render_template('mozo/takeaway_orders.html', orders=orders, title="Pedidos para Llevar", csrf_token_value=csrf_token_value)

@mozo_bp.route('/takeaway/new', methods=['GET', 'POST'])
@mozo_required
def new_takeaway_order():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        if not customer_name:
            flash('El nombre del cliente es obligatorio.', 'danger')
        else:
            new_order = Order(type='llevar', customer_name=customer_name, status='Pendiente')
            db.session.add(new_order)
            db.session.commit()
            return redirect(url_for('mozo.takeaway_order_detail', order_id=new_order.id))
    csrf_token_value = generate_csrf()
    return render_template('mozo/takeaway_form.html', action="Nuevo", title="Nuevo Pedido para Llevar", csrf_token_value=csrf_token_value)

@mozo_bp.route('/takeaway/<int:order_id>', methods=['GET', 'POST'])
@mozo_required
def takeaway_order_detail(order_id):
    order = Order.query.filter_by(id=order_id, type='llevar').first_or_404()
    if request.method == 'POST':
        if order.status == 'Pendiente':
            customer_name = request.form.get('customer_name', '').strip()
            if customer_name:
                order.customer_name = customer_name
                db.session.commit()
                flash('Nombre del cliente actualizado.', 'success')
            else:
                flash('El nombre del cliente no puede estar vacío.', 'danger')
        return redirect(url_for('mozo.takeaway_order_detail', order_id=order.id))
    products_by_category = get_products_by_category()
    csrf_token_value = generate_csrf()
    return render_template('mozo/takeaway_form.html', order=order, products_by_category=products_by_category, action="Editar", title=f"Pedido Llevar #{order.id}", csrf_token_value=csrf_token_value)

@mozo_bp.route('/takeaway/<int:order_id>/delete', methods=['POST'])
@mozo_required
def delete_takeaway_order(order_id):
    order = Order.query.filter_by(id=order_id, type='llevar').first_or_404()
    if order.status not in ['Pagado', 'Cancelado', 'Venta Anulada']:
        flash('Solo se pueden eliminar pedidos procesados.', 'warning')
    else:
        db.session.delete(order)
        db.session.commit()
        flash(f'Pedido #{order.id} eliminado de la lista.', 'success')
    return redirect(url_for('mozo.takeaway_orders_view'))