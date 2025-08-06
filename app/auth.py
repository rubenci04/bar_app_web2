from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from . import db
from flask_wtf.csrf import generate_csrf

# CORRECCIÓN: Se elimina template_folder='templates'
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('mozo.tables_view'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Nombre de usuario o contraseña inválidos.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        return redirect(url_for('admin.dashboard') if user.role == 'admin' else url_for('mozo.tables_view'))

    csrf_token_value = generate_csrf()
    return render_template('auth/login.html', title="Iniciar Sesión", csrf_token_value=csrf_token_value)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login'))
