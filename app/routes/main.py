"""Public site routes: home, static pages, search, contact, newsletter."""
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from sqlalchemy import or_, desc

from app.extensions import db
from app.models.catalog import Product, Category, Brand
from app.models.commerce import Review
from app.models.content import PageContent, NewsletterSubscriber
from app.forms.customer_forms import NewsletterForm
from app.utils.helpers import slugify, settings_value

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    active = Product.query.filter_by(status='active')
    featured = active.filter(Product.is_featured == True).limit(8).all()  # noqa: E712
    new_arrivals = active.filter(Product.is_new_arrival == True).order_by(Product.created_at.desc()).limit(8).all()  # noqa: E712
    best_sellers = active.filter(Product.is_bestseller == True).order_by(Product.sold_count.desc()).limit(8).all()  # noqa: E712
    flash_sale = active.filter(Product.is_flash_sale == True).limit(8).all()  # noqa: E712
    recommended = active.filter(Product.is_recommended == True).limit(8).all()  # noqa: E712
    discounted = active.filter(Product.old_price > Product.price).order_by(Product.created_at.desc()).limit(8).all()
    popular_cats = Category.query.filter_by(parent_id=None, status='active') \
        .order_by(Category.display_order.asc()).limit(8).all()
    popular_brands = Brand.query.filter_by(status='active').limit(8).all()
    testimonials = Review.query.filter_by(status='approved') \
        .order_by(Review.created_at.desc()).limit(6).all()

    newsletter_form = NewsletterForm()
    return render_template('customer/home.html',
                           featured=featured,
                           new_arrivals=new_arrivals,
                           best_sellers=best_sellers,
                           flash_sale=flash_sale,
                           recommended=recommended,
                           discounted=discounted,
                           popular_cats=popular_cats,
                           popular_brands=popular_brands,
                           testimonials=testimonials,
                           newsletter_form=newsletter_form)


@main_bp.route('/page/<slug>')
def page(slug):
    content = PageContent.query.filter_by(slug=slug).first_or_404()
    return render_template('customer/static_page.html', content=content)


@main_bp.route('/contact')
def contact():
    return render_template('customer/contact.html')


@main_bp.route('/faq')
def faq():
    return render_template('customer/faq.html')


@main_bp.route('/newsletter', methods=['POST'])
def newsletter():
    form = NewsletterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        sub = NewsletterSubscriber.query.filter_by(email=email).first()
        if sub:
            sub.active = True
            flash('You are already subscribed. Thank you!', 'info')
        else:
            db.session.add(NewsletterSubscriber(email=email))
            db.session.commit()
            flash('Thank you for subscribing to our newsletter!', 'success')
    else:
        flash('Please enter a valid email address.', 'danger')
    return redirect(request.referrer or url_for('main.home'))


@main_bp.route('/offers')
def offers():
    active = Product.query.filter_by(status='active')
    discounted = active.filter(Product.old_price > Product.price) \
        .order_by(desc(Product.old_price - Product.price)).all()
    return render_template('customer/offers.html', products=discounted)


@main_bp.route('/flash-sale')
def flash_sale():
    products = Product.query.filter_by(status='active', is_flash_sale=True).all()
    return render_template('customer/flash_sale.html', products=products)


@main_bp.route('/brands')
def brands():
    all_brands = Brand.query.filter_by(status='active').all()
    return render_template('customer/brands.html', brands=all_brands)


@main_bp.route('/brand/<slug>')
def brand_detail(slug):
    brand = Brand.query.filter_by(slug=slug, status='active').first_or_404()
    products = brand.active_products.all()
    return render_template('customer/brand_detail.html', brand=brand, products=products)


@main_bp.route('/categories')
def categories():
    cats = Category.query.filter_by(parent_id=None, status='active') \
        .order_by(Category.display_order.asc()).all()
    return render_template('customer/categories.html', categories=cats)


@main_bp.route('/compare', methods=['GET'])
def compare():
    ids = request.args.getlist('ids')
    products = []
    if ids:
        for pid in ids:
            try:
                p = db.session.get(Product, int(pid))
                if p and p.status == 'active' and p not in products:
                    products.append(p)
            except ValueError:
                continue
    return render_template('customer/compare.html', products=products)
