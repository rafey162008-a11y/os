"""Cart logic shared between guest (session) and logged-in (DB) carts."""
from flask import session, flash
from flask_login import current_user

from app.extensions import db
from app.models.commerce import CartItem
from app.models.catalog import Product

# Max quantity per product line
MAX_QTY = 50


class CartError(Exception):
    pass


def _guest_cart():
    return session.setdefault('cart', {})


def save_guest_cart(cart):
    session['cart'] = cart
    session.modified = True


def clear_guest_cart():
    session.pop('cart', None)
    session.modified = True


def get_cart_items():
    """Return list of (product, quantity, variant_id, item_key, unit_price, line_total)."""
    items = []
    if current_user.is_authenticated and not current_user.is_staff:
        for cart_item in CartItem.query.filter_by(user_id=current_user.id, saved_for_later=False).all():
            product = cart_item.product
            if not product:
                continue
            unit_price = float(cart_item.unit_price or product.price or 0)
            items.append({
                'key': f'db-{cart_item.id}',
                'product': product,
                'quantity': cart_item.quantity,
                'variant_id': cart_item.variant_id,
                'variant': cart_item.variant,
                'unit_price': unit_price,
                'line_total': round(unit_price * cart_item.quantity, 2),
                'is_db': True,
                'cart_item_id': cart_item.id,
            })
    else:
        for key, data in _guest_cart().items():
            product = db.session.get(Product, int(key))
            if not product:
                continue
            qty = int(data.get('qty', 1))
            unit_price = float(product.price or 0)
            items.append({
                'key': key,
                'product': product,
                'quantity': qty,
                'variant_id': None,
                'variant': None,
                'unit_price': unit_price,
                'line_total': round(unit_price * qty, 2),
                'is_db': False,
                'cart_item_id': None,
            })
    return items


def add_to_cart(product_id, qty=1, variant_id=None, saved_for_later=False):
    """Add a product to the cart. Validates stock. Returns (ok, message)."""
    product = db.session.get(Product, product_id)
    if not product:
        return False, 'Product not found.'
    if product.status != 'active':
        return False, 'This product is no longer available.'
    if product.is_out_of_stock:
        return False, 'This product is currently out of stock.'

    qty = int(qty or 1)
    if qty < 1:
        qty = 1

    if current_user.is_authenticated and not current_user.is_staff:
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id,
                                        variant_id=variant_id).first()
        if item:
            new_qty = item.quantity + qty
        else:
            item = CartItem(user_id=current_user.id, product_id=product_id,
                            variant_id=variant_id, quantity=0, saved_for_later=saved_for_later)
            db.session.add(item)
            new_qty = qty
        if new_qty > MAX_QTY:
            return False, f'Maximum quantity per product is {MAX_QTY}.'
        if product.stock_quantity is not None and new_qty > product.stock_quantity:
            return False, f'Only {product.stock_quantity} units available in stock.'
        item.quantity = new_qty
        db.session.commit()
        return True, 'Product added to cart.'
    else:
        cart = _guest_cart()
        key = str(product_id)
        current_qty = int(cart.get(key, {}).get('qty', 0))
        new_qty = current_qty + qty
        if new_qty > MAX_QTY:
            return False, f'Maximum quantity per product is {MAX_QTY}.'
        if product.stock_quantity is not None and new_qty > product.stock_quantity:
            return False, f'Only {product.stock_quantity} units available in stock.'
        cart[key] = {'qty': new_qty}
        save_guest_cart(cart)
        return True, 'Product added to cart.'


def update_cart_quantity(item_key, new_qty):
    """Update the quantity of a cart line. Returns (ok, message)."""
    try:
        new_qty = int(new_qty)
    except (TypeError, ValueError):
        return False, 'Invalid quantity.'

    if current_user.is_authenticated and not current_user.is_staff:
        item = db.session.get(CartItem, int(item_key.replace('db-', '')))
        if not item:
            return False, 'Cart item not found.'
        if new_qty <= 0:
            db.session.delete(item)
            db.session.commit()
            return True, 'Item removed from cart.'
        if new_qty > MAX_QTY:
            return False, f'Maximum quantity per product is {MAX_QTY}.'
        if item.product.stock_quantity is not None and new_qty > item.product.stock_quantity:
            return False, f'Only {item.product.stock_quantity} units available.'
        item.quantity = new_qty
        db.session.commit()
        return True, 'Cart updated.'
    else:
        cart = _guest_cart()
        if item_key not in cart:
            return False, 'Cart item not found.'
        if new_qty <= 0:
            cart.pop(item_key, None)
        else:
            if new_qty > MAX_QTY:
                return False, f'Maximum quantity per product is {MAX_QTY}.'
            product = db.session.get(Product, int(item_key))
            if product and product.stock_quantity is not None and new_qty > product.stock_quantity:
                return False, f'Only {product.stock_quantity} units available.'
            cart[item_key]['qty'] = new_qty
        save_guest_cart(cart)
        return True, 'Cart updated.'


def remove_from_cart(item_key):
    if current_user.is_authenticated and not current_user.is_staff:
        item = db.session.get(CartItem, int(item_key.replace('db-', '')))
        if item:
            db.session.delete(item)
            db.session.commit()
            return True
    else:
        cart = _guest_cart()
        if item_key in cart:
            cart.pop(item_key, None)
            save_guest_cart(cart)
            return True
    return False


def cart_totals():
    """Compute subtotal, discount(0 here), shipping, tax, grand total.

    Coupon discounts are applied at checkout. This returns structure used in templates.
    """
    items = get_cart_items()
    subtotal = round(sum(i['line_total'] for i in items), 2)
    count = sum(i['quantity'] for i in items)
    return {'items': items, 'count': count, 'subtotal': subtotal}


def cart_size():
    return sum(i['quantity'] for i in get_cart_items())


def merge_guest_cart_to_user(user):
    """Merge session guest cart into the user's DB cart after login/register."""
    cart = session.get('cart', {})
    if not cart:
        return
    for key, data in cart.items():
        try:
            product_id = int(key)
        except ValueError:
            continue
        qty = int(data.get('qty', 1))
        item = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first()
        if item:
            item.quantity = min(MAX_QTY, item.quantity + qty)
        else:
            db.session.add(CartItem(user_id=user.id, product_id=product_id, quantity=qty))
    db.session.commit()
    clear_guest_cart()


def sync_cart_after_order(order_items):
    """After an order is placed, remove the purchased items from the cart."""
    if current_user.is_authenticated and not current_user.is_staff:
        for oi in order_items:
            CartItem.query.filter_by(user_id=current_user.id, product_id=oi.product_id).delete()
        db.session.commit()
