"""Authentication routes: register, login, logout, password reset."""
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.user import User, Role
from app.models.commerce import Notification
from app.forms.customer_forms import (LoginForm, RegisterForm,
                                      ForgotPasswordForm, ResetPasswordForm)
from app.utils.helpers import settings_value
from app.utils.activity import log_action
from app.utils.decorators import staff_redirect_if_logged
from app.services.cart_service import merge_guest_cart_to_user

auth_bp = Blueprint('auth', __name__)


def _notify(user, title, message, link='#'):
    db.session.add(Notification(user_id=user.id, title=title, message=message, link=link, type='system'))


@auth_bp.route('/login', methods=['GET', 'POST'])
@staff_redirect_if_logged
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter(or_(User.email == email, User.phone == email)).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been blocked. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=form.remember.data)

            # Merge any guest cart
            if not user.is_staff:
                merge_guest_cart_to_user(user)

            log_action('login', 'user', user.id, f'{user.full_name} logged in')
            flash(f'Welcome back, {user.full_name}!', 'success')

            if user.is_staff:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.home'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
@staff_redirect_if_logged
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            address=form.address.data.strip() if form.address.data else None,
        )
        user.set_password(form.password.data)
        customer_role = Role.query.filter_by(name='Customer').first()
        if customer_role:
            user.roles.append(customer_role)
        db.session.add(user)
        db.session.flush()

        # create default address if provided
        if form.address.data and form.address.data.strip():
            from app.models.commerce import Address
            db.session.add(Address(
                customer_id=user.id,
                label='Home',
                street_address=form.address.data.strip(),
                city='',
                is_default=True,
            ))
        _notify(user, 'Welcome!', f'Thank you for registering at {settings_value("store_name", "our store")}.')
        db.session.commit()

        login_user(user)
        merge_guest_cart_to_user(user)
        log_action('register', 'user', user.id, f'New customer registered: {user.full_name}')
        flash('Registration successful. Welcome aboard!', 'success')
        return redirect(url_for('main.home'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        log_action('logout', 'user', current_user.id, f'{current_user.full_name} logged out')
        logout_user()
        flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=2)
            db.session.commit()
            # In production this would email the link; here we show it as a demo.
            flash('A password reset link has been generated. In production it is emailed to you.',
                  'info')
            flash(f'Reset link (demo): {url_for("auth.reset_password", token=token, _external=True)}',
                  'success')
        else:
            flash('No account found with that email address.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires or datetime.utcnow() > user.reset_token_expires:
        flash('This reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form, token=token)
