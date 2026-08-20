"""Customer order routes: history, detail, tracking, cancel, reorder, invoice."""
from flask import Blueprint, render_template, redirect, url_for, flash, abort, send_file, request
from flask_login import current_user
from sqlalchemy import desc

from app.extensions import db
from app.models.commerce import Order, ReturnRequest
from app.services.cart_service import add_to_cart
from app.services.order_service import update_order_status
from app.utils.decorators import customer_required
from app.utils.pdf import generate_invoice_pdf
from app.utils.helpers import settings_value

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/track')
def track():
    """Public order tracking by order number."""
    order_number = (request.args.get('order_number') or '').strip().upper()
    order = None
    if order_number:
        order = Order.query.filter_by(order_number=order_number).first()
    return render_template('customer/track_order.html', order=order, order_number=order_number)


def _get_own_order(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != current_user.id:
        abort(404)
    return order


@orders_bp.route('/confirmation/<int:order_id>')
@customer_required
def order_confirmation(order_id):
    order = _get_own_order(order_id)
    return render_template('customer/order_confirmation.html', order=order)


@orders_bp.route('/order/<int:order_id>')
@customer_required
def order_detail(order_id):
    order = _get_own_order(order_id)
    return render_template('customer/order_detail.html', order=order)


@orders_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@customer_required
def cancel_order(order_id):
    order = _get_own_order(order_id)
    if not order.can_cancel:
        flash('This order can no longer be cancelled.', 'danger')
        return redirect(url_for('orders.order_detail', order_id=order.id))
    ok, msg = update_order_status(order, 'cancelled', actor=current_user,
                                  note='Cancelled by customer.')
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('orders.order_detail', order_id=order.id))


@orders_bp.route('/order/<int:order_id>/reorder', methods=['POST'])
@customer_required
def reorder(order_id):
    order = _get_own_order(order_id)
    added = 0
    for item in order.items:
        ok, msg = add_to_cart(item.product_id, qty=item.quantity)
        if ok:
            added += 1
    if added:
        flash(f'{added} product(s) added to your cart.', 'success')
    else:
        flash('Could not reorder - products may be unavailable.', 'warning')
    return redirect(url_for('cart.view_cart'))


@orders_bp.route('/order/<int:order_id>/invoice')
@customer_required
def invoice(order_id):
    order = _get_own_order(order_id)
    pdf_bytes = generate_invoice_pdf(
        order,
        store_name=settings_value('store_name', 'ShopSphere'),
    )
    return send_file(
        __import__('io').BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'invoice-{order.order_number}.pdf',
    )
