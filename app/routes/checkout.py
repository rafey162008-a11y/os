"""Checkout routes: multi-section checkout with validation."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user

from app.extensions import db
from app.forms.customer_forms import CheckoutForm
from app.services.cart_service import cart_totals, sync_cart_after_order, get_cart_items
from app.services.order_service import place_order, OrderError, calculate_coupon_discount
from app.models.commerce import Coupon
from app.utils.decorators import customer_required
from app.utils.helpers import settings_value

checkout_bp = Blueprint('checkout', __name__)


@checkout_bp.route('/', methods=['GET', 'POST'])
@customer_required
def checkout():
    totals = cart_totals()
    items = totals['items']
    if not items:
        flash('Your cart is empty. Add some products first.', 'warning')
        return redirect(url_for('products.browse'))

    form = CheckoutForm()

    # Prefill from profile
    if request.method == 'GET' and current_user.is_authenticated:
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        default_addr = current_user.addresses.filter_by(is_default=True).first()
        if default_addr:
            form.country.data = default_addr.country
            form.province.data = default_addr.province
            form.city.data = default_addr.city
            form.area.data = default_addr.area
            form.street_address.data = default_addr.street_address
            form.postal_code.data = default_addr.postal_code

    # Live totals for display (updated by coupon via form resubmission)
    subtotal = totals['subtotal']
    coupon_code = request.form.get('coupon_code') or ''
    discount = 0.0
    coupon = None
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code.strip().upper()).first()
        if coupon and coupon.is_valid:
            discount = calculate_coupon_discount(coupon, subtotal)

    shipping_method = form.shipping_method.data or 'standard'
    free_threshold = float(settings_value('free_shipping_threshold', '100') or 100)
    flat = float(settings_value('shipping_flat', '5') or 5)
    shipping = 0.0
    if shipping_method != 'pickup':
        if subtotal < free_threshold:
            shipping = flat * 2 if shipping_method == 'express' else flat
    tax_rate = float(settings_value('tax_rate', '0') or 0)
    tax = round(subtotal * tax_rate / 100, 2)
    grand_total = round(subtotal - discount + tax + shipping, 2)

    if form.validate_on_submit():
        form_data = dict(
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
            country=form.country.data,
            province=form.province.data,
            city=form.city.data,
            area=form.area.data,
            street_address=form.street_address.data,
            postal_code=form.postal_code.data,
            shipping_method=form.shipping_method.data,
            payment_method=form.payment_method.data,
            coupon_code=form.coupon_code.data,
            notes=form.notes.data,
        )
        try:
            order = place_order(current_user, form_data, items)
        except OrderError as e:
            flash(str(e), 'danger')
            return render_template('customer/checkout.html', form=form, totals=totals,
                                   shipping=shipping, tax=tax, grand_total=grand_total,
                                   discount=discount, coupon_code=coupon_code)
        except Exception:
            db.session.rollback()
            flash('There was a problem placing your order. Please try again.', 'danger')
            return render_template('customer/checkout.html', form=form, totals=totals,
                                   shipping=shipping, tax=tax, grand_total=grand_total,
                                   discount=discount, coupon_code=coupon_code)

        sync_cart_after_order(order.items)
        return redirect(url_for('orders.order_confirmation', order_id=order.id))

    return render_template('customer/checkout.html',
                           form=form, totals=totals,
                           shipping=shipping, tax=tax, grand_total=grand_total,
                           discount=discount, coupon_code=coupon_code,
                           free_threshold=free_threshold)
