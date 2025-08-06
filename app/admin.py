from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import User
from . import db
from .utils import admin_required
from flask_login import current_user
from flask_wtf.csrf import generate_csrf

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
ITEMS_PER_PAGE = 10

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html', title="Panel de Administrador")

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
    if user.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash('No se puede eliminar al único administrador.', 'danger')
        return redirect(url_for('admin.manage_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.username} eliminado con éxito.', 'success')
    return redirect(url_for('admin.manage_users'))
