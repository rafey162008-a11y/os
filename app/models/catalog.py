"""Catalog models: categories, brands, products, variants, specifications, wishlist."""
from datetime import datetime

from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    image = db.Column(db.String(255))
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'))
    status = db.Column(db.String(20), default='active', index=True)  # active | inactive
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('Category', remote_side=[id], backref='subcategories')
    products = db.relationship('Product', backref='category', lazy='dynamic',
                               foreign_keys='Product.category_id')

    @property
    def active_products(self):
        return self.products.filter_by(status='active')

    def __repr__(self):
        return f'<Category {self.name}>'


class Brand(db.Model):
    __tablename__ = 'brands'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    logo = db.Column(db.String(255))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', backref='brand', lazy='dynamic', foreign_keys='Product.brand_id')

    @property
    def active_products(self):
        return self.products.filter_by(status='active')

    def __repr__(self):
        return f'<Brand {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'))
    subcategory_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'))
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id', ondelete='SET NULL'))

    main_image = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    short_description = db.Column(db.Text)
    description = db.Column(db.Text)

    price = db.Column(db.Numeric(12, 2), nullable=False, index=True)
    old_price = db.Column(db.Numeric(12, 2))
    cost_price = db.Column(db.Numeric(12, 2))  # for profit estimates

    stock_quantity = db.Column(db.Integer, default=0, index=True)
    min_stock_level = db.Column(db.Integer, default=5)
    sold_count = db.Column(db.Integer, default=0, index=True)

    colors = db.Column(db.String(255))  # comma separated
    sizes = db.Column(db.String(255))   # comma separated

    warranty_info = db.Column(db.Text)
    return_policy = db.Column(db.Text)
    shipping_info = db.Column(db.Text)
    condition = db.Column(db.String(30), default='new')  # new | used | refurbished

    is_featured = db.Column(db.Boolean, default=False)
    is_bestseller = db.Column(db.Boolean, default=False)
    is_new_arrival = db.Column(db.Boolean, default=False)
    is_flash_sale = db.Column(db.Boolean, default=False)
    is_recommended = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(20), default='active', index=True)  # active | inactive
    views = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship('ProductImage', backref='product', lazy='selectin',
                             cascade='all, delete-orphan', order_by='ProductImage.display_order')
    variants = db.relationship('ProductVariant', backref='product', lazy='selectin',
                               cascade='all, delete-orphan')
    specifications = db.relationship('ProductSpecification', backref='product', lazy='selectin',
                                     cascade='all, delete-orphan')
    features = db.relationship('ProductFeature', backref='product', lazy='selectin',
                               cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='product', lazy='dynamic',
                              foreign_keys='Review.product_id')
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic')

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            try:
                old = float(self.old_price)
                price = float(self.price)
                if old > 0:
                    return int(round((old - price) / old * 100))
            except (TypeError, ValueError):
                pass
        return 0

    @property
    def has_discount(self):
        return self.discount_percent > 0

    @property
    def current_price(self):
        return self.price

    @property
    def in_stock(self):
        return (self.stock_quantity or 0) > 0

    @property
    def is_low_stock(self):
        return self.stock_quantity is not None and self.min_stock_level is not None \
            and 0 < self.stock_quantity <= self.min_stock_level

    @property
    def is_out_of_stock(self):
        return (self.stock_quantity or 0) <= 0

    @property
    def rating_avg(self):
        from sqlalchemy import func
        from app.models.commerce import Review
        return db.session.query(func.coalesce(func.avg(Review.rating), 0.0)) \
            .filter(Review.product_id == self.id, Review.status == 'approved').scalar() or 0.0

    @property
    def rating_count(self):
        from app.models.commerce import Review
        return Review.query.filter_by(product_id=self.id, status='approved').count()

    @property
    def subcategory(self):
        if self.subcategory_id:
            return db.session.get(Category, self.subcategory_id)
        return None

    def __repr__(self):
        return f'<Product {self.name}>'


class ProductImage(db.Model):
    __tablename__ = 'product_images'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255))
    display_order = db.Column(db.Integer, default=0)


class ProductVariant(db.Model):
    __tablename__ = 'product_variants'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(120), nullable=False)  # e.g. 'Red / XL'
    sku = db.Column(db.String(100))
    price = db.Column(db.Numeric(12, 2))
    stock_quantity = db.Column(db.Integer, default=0)
    attributes = db.Column(db.String(255))  # JSON-ish string, e.g. '{"color":"Red","size":"XL"}'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProductSpecification(db.Model):
    __tablename__ = 'product_specifications'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    value = db.Column(db.String(255), nullable=False)


class ProductFeature(db.Model):
    __tablename__ = 'product_features'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    feature = db.Column(db.String(255), nullable=False)


class Wishlist(db.Model):
    """A wishlist is a simple many-to-many between users and products."""
    __tablename__ = 'wishlist'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', lazy='joined')

    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product'),)
