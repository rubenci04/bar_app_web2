from functools import wraps
from flask_login import current_user
from flask import abort, redirect, url_for, flash

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def mozo_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # El admin también puede acceder a las páginas de mozo
        if not current_user.is_authenticated or current_user.role not in ['admin', 'mozo']: 
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function