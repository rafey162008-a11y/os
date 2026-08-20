"""Customer account routes: profile, addresses, wishlist, orders, notifications."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from sqlalchemy import desc

from app.extensions import db
from app.models.user import User
from app.models.catalog import Product, Wishlist
from app.models.commerce import (Address, Order, Review, ReturnRequest,
                                 Notification, LoyaltyTransaction)
from app.forms.customer_forms import (ProfileForm, ChangePasswordForm, AddressForm,
                                      ReturnForm)
from app.utils.decorators import customer_required
from app.utils.helpers import save_upload, delete_upload
from app.utils.activity import log_action

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/')
@customer_required
def dashboard():
    orders = Order.query.filter_by(customer_id=current_user.id) \
        .order_by(Order.placed_at.desc()).limit(5).all()
    wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
    notifications = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).limit(5).all()
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    points = current_user.loyalty_balance
    return render_template('customer/account_dashboard.html',
                           orders=orders,
                           wishlist_count=wishlist_count,
                           notifications=notifications,
                           unread=unread,
                           points=points)


@customer_bp.route('/profile', methods=['GET', 'POST'])
@customer_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None
        if form.avatar.data:
            path = save_upload(form.avatar.data, folder='avatars')
            if path:
                if current_user.avatar:
                    delete_upload(current_user.avatar)
                current_user.avatar = path
        db.session.commit()
        log_action('update', 'user', current_user.id, 'Customer updated their profile')
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('customer.profile'))
    if request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.phone.data = current_user.phone
    return render_template('customer/profile.html', form=form)


@customer_bp.route('/change-password', methods=['GET', 'POST'])
@customer_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('customer/change_password.html', form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        db.session.add(Notification(user_id=current_user.id, title='Password Changed',
                                    message='Your password was changed successfully.'))
        db.session.commit()
        log_action('update', 'user', current_user.id, 'Customer changed their password')
        flash('Your password has been changed.', 'success')
        return redirect(url_for('customer.profile'))
    return render_template('customer/change_password.html', form=form)


# ---------------- Addresses ----------------
@customer_bp.route('/addresses')
@customer_required
def addresses():
    addrs = current_user.addresses.order_by(Address.is_default.desc()).all()
    return render_template('customer/addresses.html', addresses=addrs)


@customer_bp.route('/addresses/add', methods=['GET', 'POST'])
@customer_required
def address_add():
    form = AddressForm()
    if form.validate_on_submit():
        if form.is_default.data:
            Address.query.filter_by(customer_id=current_user.id).update({'is_default': False})
        addr = Address(
            customer_id=current_user.id,
            label=form.label.data or 'Home',
            country=form.country.data or 'Pakistan',
            province=form.province.data,
            city=form.city.data,
            area=form.area.data,
            street_address=form.street_address.data,
            postal_code=form.postal_code.data,
            phone=form.phone.data,
            is_default=form.is_default.data,
        )
        db.session.add(addr)
        db.session.commit()
        flash('Address added.', 'success')
        return redirect(url_for('customer.addresses'))
    return render_template('customer/address_form.html', form=form, title='Add Address')


@customer_bp.route('/addresses/<int:addr_id>/edit', methods=['GET', 'POST'])
@customer_required
def address_edit(addr_id):
    addr = db.session.get(Address, addr_id)
    if not addr or addr.customer_id != current_user.id:
        abort(404)
    form = AddressForm()
    if form.validate_on_submit():
        if form.is_default.data:
            Address.query.filter_by(customer_id=current_user.id).update({'is_default': False})
        addr.label = form.label.data or 'Home'
        addr.country = form.country.data or 'Pakistan'
        addr.province = form.province.data
        addr.city = form.city.data
        addr.area = form.area.data
        addr.street_address = form.street_address.data
        addr.postal_code = form.postal_code.data
        addr.phone = form.phone.data
        addr.is_default = form.is_default.data
        db.session.commit()
        flash('Address updated.', 'success')
        return redirect(url_for('customer.addresses'))
    if request.method == 'GET':
        form.label.data = addr.label
        form.country.data = addr.country
        form.province.data = addr.province
        form.city.data = addr.city
        form.area.data = addr.area
        form.street_address.data = addr.street_address
        form.postal_code.data = addr.postal_code
        form.phone.data = addr.phone
        form.is_default.data = addr.is_default
    return render_template('customer/address_form.html', form=form, title='Edit Address')


@customer_bp.route('/addresses/<int:addr_id>/delete', methods=['POST'])
@customer_required
def address_delete(addr_id):
    addr = db.session.get(Address, addr_id)
    if addr and addr.customer_id == current_user.id:
        db.session.delete(addr)
        db.session.commit()
        flash('Address deleted.', 'info')
    return redirect(url_for('customer.addresses'))


# ---------------- Orders ----------------
@customer_bp.route('/orders')
@customer_required
def my_orders():
    status = request.args.get('status', '')
    query = Order.query.filter_by(customer_id=current_user.id)
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(Order.placed_at.desc()).all()
    return render_template('customer/my_orders.html', orders=orders, current_status=status)


# ---------------- Wishlist ----------------
@customer_bp.route('/wishlist')
@customer_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id) \
        .order_by(Wishlist.created_at.desc()).all()
    return render_template('customer/wishlist.html', wishlist=items)


# ---------------- Returns ----------------
@customer_bp.route('/returns')
@customer_required
def my_returns():
    returns = ReturnRequest.query.filter_by(customer_id=current_user.id) \
        .order_by(ReturnRequest.requested_at.desc()).all()
    return render_template('customer/my_returns.html', returns=returns)


@customer_bp.route('/returns/request/<int:order_id>', methods=['GET', 'POST'])
@customer_required
def return_request(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != current_user.id:
        abort(404)
    if not order.can_request_return:
        flash('This order is not eligible for a return.', 'warning')
        return redirect(url_for('customer.my_orders'))
    form = ReturnForm()
    if form.validate_on_submit():
        evidence = None
        if form.evidence.data:
            evidence = save_upload(form.evidence.data, folder='returns')
        ret = ReturnRequest(
            order_id=order.id,
            customer_id=current_user.id,
            product_id=request.form.get('product_id', type=int) or None,
            reason=form.reason.data,
            description=form.description.data,
            evidence_images=evidence,
            status='requested',
        )
        db.session.add(ret)
        db.session.add(Notification(user_id=current_user.id, title='Return Requested',
                                    message=f'Your return request for order {order.order_number} has been submitted.'))
        db.session.commit()
        flash('Return request submitted successfully.', 'success')
        return redirect(url_for('customer.my_returns'))
    return render_template('customer/return_form.html', form=form, order=order)


# ---------------- Reviews ----------------
@customer_bp.route('/reviews')
@customer_required
def my_reviews():
    reviews = Review.query.filter_by(customer_id=current_user.id) \
        .order_by(Review.created_at.desc()).all()
    return render_template('customer/my_reviews.html', reviews=reviews)


@customer_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@customer_required
def review_delete(review_id):
    review = db.session.get(Review, review_id)
    if review and review.customer_id == current_user.id:
        if review.image:
            delete_upload(review.image)
        db.session.delete(review)
        db.session.commit()
        flash('Review deleted.', 'info')
    return redirect(url_for('customer.my_reviews'))


# ---------------- Notifications ----------------
@customer_bp.route('/notifications')
@customer_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).all()
    return render_template('customer/notifications.html', notifications=notifs)


@customer_bp.route('/notifications/read-all', methods=['POST'])
@customer_required
def notifications_read_all():
    Notification.query.filter_by(user_id=current_user.id, is_read=False) \
        .update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('customer.notifications'))


@customer_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@customer_required
def notification_read(notif_id):
    n = db.session.get(Notification, notif_id)
    if n and n.user_id == current_user.id:
        n.is_read = True
        db.session.commit()
    return redirect(url_for('customer.notifications'))
