"""Product catalog routes: browse, search, filter, sort, details."""
from flask import Blueprint, render_template, request, abort, session, redirect, url_for, flash
from sqlalchemy import or_, and_, desc, func, cast, Numeric

from app.extensions import db
from app.models.catalog import Product, Category, Brand, Wishlist
from app.models.commerce import Review
from app.services.cart_service import add_to_cart
from app.forms.customer_forms import ReviewForm

products_bp = Blueprint('products', __name__)


def _base_query():
    return Product.query.filter_by(status='active')


def _get_filtered_products(args):
    """Build a filtered + sorted product query from request args."""
    q = _base_query()
    query_text = (args.get('q') or '').strip()

    if query_text:
        pattern = f'%{query_text}%'
        q = q.filter(or_(
            Product.name.ilike(pattern),
            Product.sku.ilike(pattern),
            Product.short_description.ilike(pattern),
            Product.description.ilike(pattern),
        ))

    category_id = args.get('category', type=int)
    if category_id:
        q = q.filter(or_(
            Product.category_id == category_id,
            Product.subcategory_id == category_id,
        ))

    brand_id = args.get('brand', type=int)
    if brand_id:
        q = q.filter(Product.brand_id == brand_id)

    min_price = args.get('min_price', type=float)
    max_price = args.get('max_price', type=float)
    if min_price is not None:
        q = q.filter(Product.price >= min_price)
    if max_price is not None:
        q = q.filter(Product.price <= max_price)

    rating = args.get('rating', type=int)
    if rating and rating >= 1:
        q = q.filter(Product.id.in_(
            db.session.query(Review.product_id)
            .filter(Review.status == 'approved')
            .group_by(Review.product_id)
            .having(func.avg(Review.rating) >= rating)
        ))

    availability = args.get('availability')
    if availability == 'in_stock':
        q = q.filter(Product.stock_quantity > 0)
    elif availability == 'out_of_stock':
        q = q.filter(Product.stock_quantity <= 0)

    discount = args.get('discount')
    if discount == 'yes':
        q = q.filter(Product.old_price > Product.price)

    condition = args.get('condition')
    if condition:
        q = q.filter(Product.condition == condition)

    sort = args.get('sort', 'newest')
    if sort == 'price_asc':
        q = q.order_by(Product.price.asc())
    elif sort == 'price_desc':
        q = q.order_by(Product.price.desc())
    elif sort == 'oldest':
        q = q.order_by(Product.created_at.asc())
    elif sort == 'best_selling':
        q = q.order_by(Product.sold_count.desc())
    elif sort == 'biggest_discount':
        q = q.order_by(desc(Product.old_price - Product.price))
    elif sort == 'name':
        q = q.order_by(Product.name.asc())
    else:  # newest, highest_rated, most_popular
        q = q.order_by(Product.created_at.desc())

    return q, query_text


@products_bp.route('/products')
def browse():
    args = request.args
    query, query_text = _get_filtered_products(args)

    page = args.get('page', 1, type=int)
    per_page = 12
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    # Filter facets
    categories = Category.query.filter_by(status='active').order_by(Category.name.asc()).all()
    brands = Brand.query.filter_by(status='active').order_by(Brand.name.asc()).all()
    min_price_f = args.get('min_price', type=float)
    max_price_f = args.get('max_price', type=float)

    # Search history (session based)
    history = session.get('search_history', [])
    if query_text:
        if query_text in history:
            history.remove(query_text)
        history.insert(0, query_text)
        session['search_history'] = history[:8]
        session.modified = True

    return render_template('customer/products.html',
                           products=products,
                           pagination=pagination,
                           query=query_text,
                           categories=categories,
                           brands=brands,
                           total=query.count(),
                           args=args)


@products_bp.route('/search')
def search():
    """Dedicated search page (same engine as browse)."""
    return browse()


@products_bp.route('/search/suggest')
def search_suggest():
    """JSON suggestions endpoint for the live search box."""
    from flask import jsonify
    q = (request.args.get('q') or '').strip()
    if len(q) < 1:
        return jsonify([])
    pattern = f'%{q}%'
    matches = Product.query.filter(
        Product.status == 'active',
        or_(Product.name.ilike(pattern), Product.sku.ilike(pattern))
    ).limit(8).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'image': p.main_image or '',
        'price': float(p.price) if p.price else 0,
    } for p in matches])


@products_bp.route('/product/<slug>')
def detail(slug):
    product = Product.query.filter_by(slug=slug, status='active').first_or_404()
    product.views = (product.views or 0) + 1
    db.session.commit()

    # Recently viewed (session based)
    viewed = session.get('recently_viewed', [])
    if product.id in viewed:
        viewed.remove(product.id)
    viewed.insert(0, product.id)
    session['recently_viewed'] = viewed[:6]
    session.modified = True

    reviews = Review.query.filter_by(product_id=product.id, status='approved') \
        .order_by(Review.created_at.desc()).all()

    # Related products (same category, exclude self)
    related = []
    if product.category_id:
        related = _base_query().filter(
            Product.category_id == product.category_id,
            Product.id != product.id
        ).limit(4).all()
    if len(related) < 4:
        extra = _base_query().filter(Product.id != product.id).limit(4).all()
        for p in extra:
            if p not in related and len(related) < 4:
                related.append(p)

    # Recently viewed products objects
    recent_products = []
    for pid in session.get('recently_viewed', []):
        p = db.session.get(Product, pid)
        if p and p.id != product.id and p.status == 'active' and p not in recent_products:
            recent_products.append(p)

    review_form = ReviewForm()
    is_wishlisted = False
    from flask_login import current_user
    if current_user.is_authenticated and not current_user.is_staff:
        is_wishlisted = Wishlist.query.filter_by(user_id=current_user.id,
                                                 product_id=product.id).first() is not None

    return render_template('customer/product_detail.html',
                           product=product,
                           reviews=reviews,
                           related=related,
                           recent_products=recent_products,
                           review_form=review_form,
                           is_wishlisted=is_wishlisted)


@products_bp.route('/category/<slug>')
def category(slug):
    category = Category.query.filter_by(slug=slug, status='active').first_or_404()
    # Include products from subcategories
    sub_ids = [c.id for c in category.subcategories if c.status == 'active']
    ids = [category.id] + sub_ids
    products = Product.query.filter(
        Product.status == 'active',
        or_(Product.category_id.in_(ids), Product.subcategory_id.in_(ids))
    ).order_by(Product.created_at.desc()).all()
    return render_template('customer/category_detail.html',
                           category=category,
                           products=products,
                           subcategories=category.subcategories)


@products_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
def wishlist_add(product_id):
    from flask_login import login_required, current_user
    from app.utils.decorators import customer_required

    # Simple auth check
    if not current_user.is_authenticated or current_user.is_staff:
        flash('Please log in to add products to your wishlist.', 'warning')
        return redirect(url_for('auth.login'))
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        flash('This product is already in your wishlist.', 'info')
    else:
        db.session.add(Wishlist(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        flash('Product added to your wishlist.', 'success')
    return redirect(request.referrer or url_for('products.detail', slug=product.slug))


@products_bp.route('/wishlist/remove/<int:product_id>', methods=['POST'])
def wishlist_remove(product_id):
    from flask_login import current_user
    if current_user.is_authenticated and not current_user.is_staff:
        Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
        db.session.commit()
        flash('Product removed from your wishlist.', 'info')
    return redirect(request.referrer or url_for('main.home'))


@products_bp.route('/wishlist/move-to-cart/<int:product_id>', methods=['POST'])
def wishlist_move_to_cart(product_id):
    from flask_login import current_user
    if current_user.is_authenticated and not current_user.is_staff:
        ok, msg = add_to_cart(product_id, qty=1)
        if ok:
            Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
            db.session.commit()
            flash('Product moved to your cart.', 'success')
        else:
            flash(msg, 'danger')
    return redirect(request.referrer or url_for('main.home'))
