"""Access-control decorators for role-based permissions."""
from functools import wraps

from flask import abort, redirect, url_for, flash
from flask_login import current_user, login_required


def admin_required(view):
    """Require an authenticated staff user (any staff role)."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_staff:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def permission_required(permission):
    """Require a specific backend permission. Super Admin bypasses."""
    def decorator(view):
        @wraps(view)
        @admin_required
        def wrapped(*args, **kwargs):
            if not current_user.has_permission(permission):
                flash(f'You do not have permission to access this page ({permission}).', 'danger')
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def customer_required(view):
    """Require a logged-in customer (non-staff) account."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.is_staff:
            flash('This page is for customer accounts only.', 'warning')
            return redirect(url_for('admin.dashboard'))
        if not current_user.is_active:
            flash('Your account has been blocked. Contact support.', 'danger')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def staff_redirect_if_logged(view):
    """If a staff user visits a customer auth page, send them to admin dashboard."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_staff:
            return redirect(url_for('admin.dashboard'))
        return view(*args, **kwargs)
    return wrapped
