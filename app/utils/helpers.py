"""Template helpers and misc utilities."""
import os
import uuid
import re
from datetime import datetime

from flask import request, session, url_for, current_app
from werkzeug.utils import secure_filename


def currency(amount):
    """Format a number as a currency string using store settings."""
    if amount is None:
        amount = 0
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0
    sym = 'Rs.' if current_app and current_app.config.get('STORE_CURRENCY') == 'Rs.' else '$'
    # Default symbol from config
    sym = current_app.config.get('STORE_CURRENCY', '$') if current_app else '$'
    if amount == int(amount):
        return f'{sym}{amount:,.0f}'
    return f'{sym}{amount:,.2f}'


def money(amount):
    """Alias for currency with 2 decimals always."""
    if amount is None:
        amount = 0
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0
    sym = current_app.config.get('STORE_CURRENCY', '$') if current_app else '$'
    return f'{sym}{amount:,.2f}'


def status_badge(status):
    """Return a Bootstrap badge HTML snippet for a status value."""
    from app.utils.constants import STATUS_BADGE_MAP
    status = (status or '').lower()
    color = STATUS_BADGE_MAP.get(status, 'secondary')
    label = status.replace('_', ' ').title() if status else 'N/A'
    return f'<span class="badge bg-{color} status-badge">{label}</span>'


def avg_rating(product):
    try:
        return round(float(product.rating_avg), 1)
    except (TypeError, ValueError, AttributeError):
        return 0.0


def review_count(product):
    try:
        return int(product.rating_count)
    except (TypeError, ValueError, AttributeError):
        return 0


def settings_value(key, default=None):
    """Fetch a value from the settings table with caching."""
    from app.models.content import Setting
    cached = getattr(current_app, '_settings_cache', None)
    if cached is None:
        cached = {s.key: s.value for s in Setting.query.all()}
        current_app._settings_cache = cached
    return cached.get(key, default)


def cart_count():
    """Total quantity of items in the user's cart (for navbar badge)."""
    from flask_login import current_user
    from app.models.commerce import CartItem
    from app.models.catalog import Product
    if current_user.is_authenticated and not current_user.is_staff:
        total = 0
        items = CartItem.query.filter_by(user_id=current_user.id, saved_for_later=False).all()
        for item in items:
            product = item.product
            if product and product.status == 'active':
                total += item.quantity
        return total
    # Guest cart stored in session
    cart = session.get('cart', {})
    return sum(int(v.get('qty', 0)) for v in cart.values())


def is_staff():
    from flask_login import current_user
    return current_user.is_authenticated and current_user.is_staff


def slugify(text):
    """Convert text into a URL-friendly slug."""
    text = (text or '').lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def unique_slug(model, text):
    """Generate a unique slug for a model that has a 'slug' column."""
    base = slugify(text) or 'item'
    slug = base
    n = 1
    while model.query.filter_by(slug=slug).first() is not None:
        n += 1
        slug = f'{base}-{n}'
    return slug


def unique_sku(model, prefix='SKU'):
    base = f'{prefix}-{uuid.uuid4().hex[:8].upper()}'
    while model.query.filter_by(sku=base).first() is not None:
        base = f'{prefix}-{uuid.uuid4().hex[:8].upper()}'
    return base


def save_upload(file_storage, folder='products'):
    """Save an uploaded image and return its relative URL path."""
    from app.extensions import db
    filename = secure_filename(file_storage.filename or '')
    if not filename:
        return None
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', set()):
        return None
    new_name = f'{uuid.uuid4().hex}_{filename}'
    folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
    os.makedirs(folder_path, exist_ok=True)
    file_storage.save(os.path.join(folder_path, new_name))
    return f'uploads/{folder}/{new_name}'


def delete_upload(relative_path):
    """Delete an uploaded file by its relative URL path if it exists."""
    if not relative_path:
        return
    full = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_path.replace('uploads/', '', 1))
    # ensure path stays within upload folder
    if os.path.abspath(full).startswith(os.path.abspath(current_app.config['UPLOAD_FOLDER'])):
        if os.path.exists(full):
            try:
                os.remove(full)
            except OSError:
                pass


def product_image_url(image_path):
    """Return the URL for an image path or a placeholder."""
    if image_path:
        return url_for('static', filename=image_path)
    return url_for('static', filename='images/placeholder.png')


def update_settings_cache(app):
    """Refresh the in-memory settings cache."""
    from app.models.content import Setting
    with app.app_context():
        app._settings_cache = {s.key: s.value for s in Setting.query.all()}
