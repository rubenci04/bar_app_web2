from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from . import db
from flask_wtf.csrf import generate_csrf # <--- IMPORTANTE: Añadir esta importación

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        else: # mozo
            return redirect(url_for('mozo.tables_view'))

    if request.method == 'POST':
        # Flask-WTF valida el token automáticamente aquí en el backend
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Nombre de usuario o contraseña inválidos. Por favor, inténtalo de nuevo.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        else: # mozo
            return redirect(url_for('mozo.tables_view'))

    # --- CAMBIO IMPORTANTE PARA GET ---
    # Generar el valor del token y pasarlo a la plantilla
    csrf_token_value = generate_csrf()
    return render_template('auth/login.html', title="Iniciar Sesión", csrf_token_value=csrf_token_value)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login'))