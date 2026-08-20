"""Product review routes (customer-facing)."""
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import current_user

from app.extensions import db
from app.models.catalog import Product
from app.models.commerce import Review, Order
from app.forms.customer_forms import ReviewForm
from app.utils.decorators import customer_required
from app.utils.helpers import save_upload, delete_upload

reviews_bp = Blueprint('reviews', __name__)


def _has_purchased(user_id, product_id):
    """Check if the user has a delivered order containing this product."""
    from app.models.commerce import OrderItem
    return db.session.query(OrderItem.id) \
        .join(Order, Order.id == OrderItem.order_id) \
        .filter(Order.customer_id == user_id,
                Order.status == 'delivered',
                OrderItem.product_id == product_id).first() is not None


@reviews_bp.route('/product/<int:product_id>/review', methods=['GET', 'POST'])
@customer_required
def add_review(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    existing = Review.query.filter_by(product_id=product_id,
                                      customer_id=current_user.id).first()
    if existing:
        flash('You have already reviewed this product.', 'info')
        return redirect(url_for('products.detail', slug=product.slug))

    verified = _has_purchased(current_user.id, product_id)

    form = ReviewForm()
    if form.validate_on_submit():
        image = None
        if form.image.data:
            image = save_upload(form.image.data, folder='reviews')
        review = Review(
            product_id=product.id,
            customer_id=current_user.id,
            rating=form.rating.data,
            title=form.title.data,
            comment=form.comment.data,
            image=image,
            status='pending',
            verified_purchase=verified,
        )
        db.session.add(review)
        db.session.commit()
        flash('Thank you! Your review has been submitted and is awaiting approval.', 'success')
        return redirect(url_for('products.detail', slug=product.slug))

    return render_template('customer/review_form.html',
                           form=form, product=product, verified=verified)


@reviews_bp.route('/review/<int:review_id>/edit', methods=['GET', 'POST'])
@customer_required
def edit_review(review_id):
    review = db.session.get(Review, review_id)
    if not review or review.customer_id != current_user.id:
        abort(404)
    form = ReviewForm()
    if form.validate_on_submit():
        review.rating = form.rating.data
        review.title = form.title.data
        review.comment = form.comment.data
        if form.image.data:
            new_image = save_upload(form.image.data, folder='reviews')
            if new_image:
                if review.image:
                    delete_upload(review.image)
                review.image = new_image
        review.status = 'pending'  # re-approval after edit
        db.session.commit()
        flash('Your review has been updated and is awaiting re-approval.', 'success')
        return redirect(url_for('customer.my_reviews'))
    if request.method == 'GET':
        form.rating.data = review.rating
        form.title.data = review.title
        form.comment.data = review.comment
    return render_template('customer/review_form.html', form=form,
                           product=review.product, verified=review.verified_purchase)
