"""Shopping cart routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user

from app.extensions import db
from app.models.commerce import CartItem
from app.services.cart_service import (add_to_cart, update_cart_quantity,
                                       remove_from_cart, cart_totals, get_cart_items)
from app.utils.helpers import settings_value

cart_bp = Blueprint('cart', __name__)


@cart_bp.route('/')
def view_cart():
    totals = cart_totals()
    # Shipping / tax preview
    subtotal = totals['subtotal']
    free_threshold = float(settings_value('free_shipping_threshold', '100') or 100)
    flat = float(settings_value('shipping_flat', '5') or 5)
    shipping = 0.0 if subtotal >= free_threshold else flat
    tax_rate = float(settings_value('tax_rate', '0') or 0)
    tax = round(subtotal * tax_rate / 100, 2)
    grand = round(subtotal + shipping + tax, 2)
    return render_template('customer/cart.html',
                           totals=totals,
                           shipping=shipping,
                           tax=tax,
                           grand_total=grand,
                           free_threshold=free_threshold)


@cart_bp.route('/add', methods=['POST'])
def add():
    product_id = request.form.get('product_id', type=int)
    qty = request.form.get('quantity', 1, type=int)
    variant_id = request.form.get('variant_id', type=int) or None
    if not product_id:
        flash('Invalid product.', 'danger')
        return redirect(url_for('main.home'))
    ok, msg = add_to_cart(product_id, qty=qty, variant_id=variant_id)
    flash(msg, 'success' if ok else 'danger')
    action = request.form.get('action')
    if action == 'buy_now':
        return redirect(url_for('checkout.checkout'))
    return redirect(request.referrer or url_for('products.browse'))


@cart_bp.route('/update/<item_key>', methods=['POST'])
def update(item_key):
    qty = request.form.get('quantity', 1, type=int)
    ok, msg = update_cart_quantity(item_key, qty)
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/remove/<item_key>', methods=['POST'])
def remove(item_key):
    remove_from_cart(item_key)
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/save-for-later/<item_key>', methods=['POST'])
def save_for_later(item_key):
    if current_user.is_authenticated and not current_user.is_staff:
        item = db.session.get(CartItem, int(item_key.replace('db-', '')))
        if item:
            item.saved_for_later = True
            db.session.commit()
            flash('Item saved for later.', 'info')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/count')
def count():
    totals = cart_totals()
    return jsonify({'count': totals['count']})
