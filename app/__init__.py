"""Application factory for the Online Shopping System."""
import os
from flask import Flask, render_template, request
from datetime import datetime

from config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- Template globals & context processors ---
    from app.utils.helpers import (
        currency, money, status_badge, avg_rating, review_count,
        settings_value, cart_count, is_staff, product_image_url
    )
    from app.models.content import Setting, Banner

    @app.context_processor
    def inject_globals():
        from app.models.catalog import Category
        cats = Category.query.filter_by(parent_id=None, status='active') \
            .order_by(Category.display_order.asc(), Category.name.asc()).all()
        banners = Banner.query.filter_by(active=True) \
            .order_by(Banner.display_order.asc()).all()
        return dict(
            store_name=settings_value('store_name', 'ShopSphere'),
            store_currency=currency,
            money=money,
            status_badge=status_badge,
            avg_rating=avg_rating,
            review_count=review_count,
            settings_value=settings_value,
            cart_count=cart_count,
            is_staff=is_staff,
            product_image_url=product_image_url,
            categories=cats,
            banners=banners,
            search_query=request.args.get('q', ''),
            now=datetime.utcnow(),
        )

    # Register helpers as true Jinja globals so they are always available,
    # including inside imported macros (e.g. customer/macros.html).
    app.add_template_global(product_image_url)
    app.add_template_global(currency, 'currency')
    app.add_template_global(money, 'money')
    app.add_template_global(status_badge, 'status_badge')
    app.add_template_global(avg_rating, 'avg_rating')
    app.add_template_global(review_count, 'review_count')
    app.add_template_global(settings_value, 'settings_value')
    app.add_template_global(cart_count, 'cart_count')
    app.add_template_global(is_staff, 'is_staff')

    # --- Register blueprints ---
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.products import products_bp
    from app.routes.cart import cart_bp
    from app.routes.checkout import checkout_bp
    from app.routes.orders import orders_bp
    from app.routes.customer import customer_bp
    from app.routes.reviews import reviews_bp
    from app.routes.support import support_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(checkout_bp, url_prefix='/checkout')
    app.register_blueprint(orders_bp)
    app.register_blueprint(customer_bp, url_prefix='/account')
    app.register_blueprint(reviews_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def too_large(e):
        return render_template('errors/413.html'), 413

    # Create tables on first run (development convenience)
    with app.app_context():
        db.create_all()

    return app
