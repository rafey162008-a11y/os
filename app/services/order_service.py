"""Order placement, inventory, coupon and notification business logic."""
from datetime import datetime

from flask_login import current_user

from app.extensions import db
from app.models.commerce import (Order, OrderItem, Payment, Shipment, Coupon,
                                 Notification, LoyaltyTransaction)
from app.models.catalog import Product
from app.models.business import InventoryMovement
from app.utils.helpers import settings_value


class OrderError(Exception):
    pass


def calculate_coupon_discount(coupon, subtotal):
    """Compute the discount value a coupon applies to a subtotal."""
    if not coupon or not coupon.is_valid:
        return 0.0
    try:
        subtotal = float(subtotal)
    except (TypeError, ValueError):
        return 0.0
    min_purchase = float(coupon.min_purchase or 0)
    if subtotal < min_purchase:
        return 0.0
    amount = float(coupon.discount_amount or 0)
    if coupon.discount_type == 'percentage':
        discount = subtotal * (amount / 100.0)
        max_discount = float(coupon.max_discount or 0)
        if max_discount and discount > max_discount:
            discount = max_discount
    else:
        discount = min(amount, subtotal)
    return round(discount, 2)


def get_tax_rate():
    try:
        return float(settings_value('tax_rate', '0') or 0) / 100.0
    except (TypeError, ValueError):
        return 0.0


def get_shipping_charge(shipping_method, subtotal):
    """Compute shipping charge based on method and free-shipping threshold."""
    if shipping_method == 'pickup':
        return 0.0
    free_threshold = float(settings_value('free_shipping_threshold', '100') or 100)
    flat = float(settings_value('shipping_flat', '5') or 5)
    if subtotal >= free_threshold:
        return 0.0
    if shipping_method == 'express':
        return round(flat * 2, 2)
    return round(flat, 2)


def place_order(customer, form_data, cart_items):
    """Create an order, its items, payment, shipment; update stock and cart.

    Returns the created Order. Raises OrderError if validation fails.
    """
    # 1. Validate stock for every item
    for item in cart_items:
        product = item['product']
        qty = item['quantity']
        if product.status != 'active':
            raise OrderError(f'"{product.name}" is no longer available.')
        if product.stock_quantity is not None and qty > product.stock_quantity:
            raise OrderError(f'Only {product.stock_quantity} units of "{product.name}" are in stock.')

    # 2. Totals
    subtotal = round(sum(i['line_total'] for i in cart_items), 2)

    # 3. Coupon
    coupon = None
    coupon_code = (form_data.get('coupon_code') or '').strip().upper()
    discount = 0.0
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if not coupon:
            raise OrderError('Invalid coupon code.')
        if not coupon.is_valid:
            if coupon.expired:
                raise OrderError('This coupon has expired.')
            raise OrderError('This coupon is no longer valid.')
        discount = calculate_coupon_discount(coupon, subtotal)
        if discount <= 0:
            raise OrderError('This coupon cannot be applied to your order.')

    # 4. Tax and shipping
    tax_rate = get_tax_rate()
    tax = round(subtotal * tax_rate, 2)
    shipping_method = form_data.get('shipping_method', 'standard')
    shipping = get_shipping_charge(shipping_method, subtotal)
    grand_total = round(subtotal - discount + tax + shipping, 2)

    # 5. Build shipping address text
    address_parts = [
        form_data.get('full_name', ''),
        form_data.get('street_address', ''),
        form_data.get('area', ''),
        form_data.get('city', ''),
        form_data.get('province', ''),
        form_data.get('country', ''),
        form_data.get('postal_code', ''),
        form_data.get('phone', ''),
    ]
    shipping_address = '\n'.join(p for p in address_parts if p)

    # 6. Create order
    order = Order(
        customer_id=customer.id,
        coupon_id=coupon.id if coupon else None,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        shipping_charge=shipping,
        grand_total=grand_total,
        shipping_method=shipping_method,
        shipping_address=shipping_address,
        status='pending',
        payment_status='pending',
        notes=form_data.get('notes') or '',
    )
    db.session.add(order)
    db.session.flush()  # get order.id

    # 7. Order items + stock update + inventory movement
    for item in cart_items:
        product = item['product']
        qty = item['quantity']
        unit_price = item['unit_price']
        oi = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            variant_label=item.get('variant').name if item.get('variant') else None,
            unit_price=unit_price,
            quantity=qty,
            discount=0,
            line_total=round(unit_price * qty, 2),
        )
        db.session.add(oi)
        # decrease stock
        product.stock_quantity = (product.stock_quantity or 0) - qty
        product.sold_count = (product.sold_count or 0) + qty
        db.session.add(InventoryMovement(
            product_id=product.id,
            user_id=customer.id,
            quantity_change=-qty,
            reason='sale',
            reference_type='order',
            reference_id=order.id,
            stock_after=product.stock_quantity,
        ))

    # 8. Payment record
    payment_method = form_data.get('payment_method', 'cod')
    payment = Payment(
        order_id=order.id,
        method=payment_method,
        amount=grand_total,
        status='pending' if payment_method == 'cod' else 'processing',
    )
    db.session.add(payment)

    # 9. Shipment
    shipment = Shipment(order_id=order.id, delivery_status='not_shipped')
    db.session.add(shipment)

    # 10. Coupon usage increment
    if coupon:
        coupon.used_count = (coupon.used_count or 0) + 1

    # 11. Loyalty points (e.g. 1 point per $10 spent, rounded down)
    points = int(grand_total // 10)
    if points > 0:
        db.session.add(LoyaltyTransaction(
            user_id=customer.id,
            points=points,
            reason=f'Points earned on order {order.order_number}',
            reference_type='purchase',
            reference_id=order.id,
        ))

    # 12. Notification
    db.session.add(Notification(
        user_id=customer.id,
        title='Order Placed',
        message=f'Your order {order.order_number} has been placed successfully.',
        link=f'/account/orders/{order.id}',
        type='order',
    ))

    db.session.commit()
    return order


def update_order_status(order, new_status, actor=None, note=None):
    """Transition an order to a new status, adjusting inventory and notifications.

    Returns a tuple (success, message).
    """
    old_status = order.status
    valid = {'pending', 'confirmed', 'processing', 'packed', 'shipped',
             'out_for_delivery', 'delivered', 'cancelled', 'failed'}
    if new_status not in valid:
        return False, 'Invalid status.'

    # Prevent already final orders from being changed
    if old_status in ('cancelled', 'returned', 'refunded') and new_status not in ('refunded', 'returned'):
        return False, f'Order is already {old_status}; cannot change to {new_status}.'

    # Inventory restoration on cancellation
    if new_status == 'cancelled' and old_status not in ('cancelled', 'returned', 'refunded'):
        for item in order.items:
            product = item.product
            if product:
                product.stock_quantity = (product.stock_quantity or 0) + item.quantity
                product.sold_count = max(0, (product.sold_count or 0) - item.quantity)
                db.session.add(InventoryMovement(
                    product_id=product.id,
                    user_id=actor.id if actor else None,
                    quantity_change=item.quantity,
                    reason='cancellation',
                    reference_type='order',
                    reference_id=order.id,
                    stock_after=product.stock_quantity,
                ))

    order.status = new_status
    if new_status == 'delivered':
        order.payment_status = 'paid' if order.payment_status != 'failed' else order.payment_status
        if order.shipment:
            order.shipment.delivery_status = 'delivered'
            order.shipment.delivered_at = datetime.utcnow()

    # Notification to customer
    db.session.add(Notification(
        user_id=order.customer_id,
        title='Order Status Updated',
        message=f'Your order {order.order_number} is now {new_status.replace("_", " ")}.',
        link=f'/account/orders/{order.id}',
        type='order',
    ))

    if note:
        order.notes = (order.notes or '') + f'\n[{datetime.utcnow().strftime("%Y-%m-%d %H:%M")}] {note}'

    db.session.commit()
    return True, f'Order status updated to {new_status.replace("_", " ")}.'
