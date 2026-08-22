"""Seed script for the Online Shopping System.

Creates default roles, an admin user, store settings, sample categories,
brands and products so the application is usable immediately after setup.

Usage:
    python seed.py
"""
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from app import create_app
from app.extensions import db
from app.models.user import User, Role, Permission
from app.models.catalog import Category, Brand, Product
from app.models.content import Setting, Banner, PageContent
from app.utils.constants import PERMISSIONS, USER_ROLES

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


def seed_roles():
    print("Seeding roles...")
    role_permissions = {
        'Super Admin': PERMISSIONS,
        'Admin': PERMISSIONS,
        'Sales Manager': ['manage_orders', 'manage_payments', 'manage_coupons',
                           'manage_offers', 'view_reports', 'manage_customers'],
        'Inventory Manager': ['manage_products', 'manage_categories', 'manage_brands',
                              'manage_inventory', 'manage_suppliers'],
        'Order Manager': ['manage_orders', 'manage_delivery', 'manage_returns', 'manage_refunds'],
        'Delivery Manager': ['manage_delivery', 'manage_orders'],
        'Customer Support': ['manage_support', 'manage_reviews', 'manage_customers'],
        'Supplier': ['manage_products'],
        'Customer': [],
    }
    for role_name in USER_ROLES:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f"{role_name} role")
            db.session.add(role)
            db.session.flush()
        perms = role_permissions.get(role_name, [])
        # clear existing perms then re-add
        Permission.query.filter_by(role_id=role.id).delete()
        for p in perms:
            db.session.add(Permission(role_id=role.id, name=p))
    db.session.commit()


def seed_admin():
    print("Seeding admin user...")
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@shop.com').lower().strip()
    admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@123')
    admin_name = os.environ.get('ADMIN_NAME', 'Super Admin')
    admin_role = Role.query.filter_by(name='Super Admin').first()
    admin = User.query.filter_by(email=admin_email).first()
    if admin:
        # Always (re)set password from .env so re-running seed resets admin access.
        admin.set_password(admin_password)
        admin.is_staff = True
        admin.is_active = True
        admin.is_verified = True
        if admin_role and admin_role not in admin.roles:
            admin.roles.append(admin_role)
        db.session.commit()
        print(f"Admin password updated for {admin_email}.")
        return
    admin = User(full_name=admin_name, email=admin_email,
                 phone='+1234567890', is_staff=True, is_active=True, is_verified=True)
    admin.set_password(admin_password)
    if admin_role:
        admin.roles.append(admin_role)
    db.session.add(admin)
    db.session.commit()
    print(f"Admin user created: {admin_email}")


def seed_settings():
    print("Seeding settings...")
    defaults = {
        'store_name': 'ShopSphere',
        'store_currency': '$',
        'tax_rate': '5',
        'shipping_flat': '5',
        'free_shipping_threshold': '100',
        'contact_email': 'support@shopsphere.com',
        'contact_phone': '+1234567890',
        'address': '123 Commerce St, Business City',
        'facebook': '', 'twitter': '', 'instagram': '',
    }
    for k, v in defaults.items():
        if not Setting.query.filter_by(key=k).first():
            db.session.add(Setting(key=k, value=v))
    db.session.commit()


def seed_catalog():
    print("Seeding catalog...")
    if Category.query.count() > 0:
        print("Categories exist, skipping catalog seed.")
        return

    categories = [
        ('Electronics', 'Gadgets and devices'),
        ('Fashion', 'Clothing and accessories'),
        ('Home & Kitchen', 'Everything for your home'),
        ('Books', 'Read and learn'),
        ('Sports', 'Gear for an active life'),
    ]
    cat_objs = {}
    for name, desc in categories:
        c = Category(name=name, slug=name.lower().replace(' & ', '-').replace(' ', '-'),
                     description=desc, status='active', display_order=len(cat_objs))
        db.session.add(c)
        db.session.flush()
        cat_objs[name] = c

    subcats = {
        'Electronics': ['Phones', 'Laptops', 'Audio'],
        'Fashion': ['Men', 'Women', 'Shoes'],
        'Home & Kitchen': ['Furniture', 'Cookware'],
        'Books': ['Fiction', 'Non-Fiction'],
        'Sports': ['Fitness', 'Outdoor'],
    }
    for parent, subs in subcats.items():
        for s in subs:
            db.session.add(Category(name=s, slug=s.lower().replace(' ', '-'),
                                    parent_id=cat_objs[parent].id, status='active'))

    brands = ['Apple', 'Samsung', 'Nike', 'Sony', 'IKEA', 'Adidas']
    brand_objs = []
    for b in brands:
        br = Brand(name=b, slug=b.lower(), status='active')
        db.session.add(br)
        db.session.flush()
        brand_objs.append(br)

    sample_products = [
        ('Smartphone X', 'Electronics', 'Phones', 'Apple', 799.0, 899.0, 50),
        ('Laptop Pro 15', 'Electronics', 'Laptops', 'Apple', 1499.0, 1699.0, 30),
        ('Wireless Earbuds', 'Electronics', 'Audio', 'Sony', 129.0, 159.0, 100),
        ('Men T-Shirt', 'Fashion', 'Men', 'Nike', 19.0, 25.0, 200),
        ('Running Shoes', 'Fashion', 'Shoes', 'Adidas', 89.0, 110.0, 80),
        ('Office Chair', 'Home & Kitchen', 'Furniture', 'IKEA', 149.0, 179.0, 40),
        ('Cookware Set', 'Home & Kitchen', 'Cookware', 'IKEA', 59.0, 79.0, 60),
        ('Fitness Tracker', 'Sports', 'Fitness', 'Samsung', 49.0, 69.0, 120),
    ]
    for name, cat, sub, brand, price, old, stock in sample_products:
        parent = cat_objs.get(cat)
        subcat = Category.query.filter_by(name=sub).first()
        brand_obj = Brand.query.filter_by(name=brand).first()
        p = Product(
            name=name, slug=name.lower().replace(' ', '-') + '-' + str(random.randint(100, 999)),
            sku='SKU-' + str(random.randint(10000, 99999)),
            category_id=parent.id if parent else None,
            subcategory_id=subcat.id if subcat else None,
            brand_id=brand_obj.id if brand_obj else None,
            price=price, old_price=old, cost_price=round(price * 0.6, 2),
            stock_quantity=stock, min_stock_level=10,
            short_description=f"High quality {name}.",
            description=f"The {name} is a premium product with excellent features and build quality.",
            condition='new', status='active',
            is_featured=random.choice([True, False]),
            is_bestseller=random.choice([True, False]),
            is_new_arrival=random.choice([True, False]),
        )
        db.session.add(p)
    db.session.commit()


def seed_content():
    print("Seeding content...")
    if not Banner.query.first():
        db.session.add(Banner(title='Welcome to ShopSphere', subtitle='Best deals every day',
                              position='home_hero', active=True, display_order=0))
    if not PageContent.query.filter_by(slug='about').first():
        db.session.add(PageContent(slug='about', title='About Us',
                                   content='<p>ShopSphere is your one-stop online shopping destination.</p>'))
    if not PageContent.query.filter_by(slug='terms').first():
        db.session.add(PageContent(slug='terms', title='Terms & Conditions',
                                   content='<p>By using this site you agree to our terms.</p>'))
    if not PageContent.query.filter_by(slug='privacy').first():
        db.session.add(PageContent(slug='privacy', title='Privacy Policy',
                                   content='<p>We respect your privacy.</p>'))
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        seed_roles()
        seed_admin()
        seed_settings()
        seed_catalog()
        seed_content()
        print("\nSeed complete! Admin login: admin@shopsphere.com / admin123")


if __name__ == '__main__':
    main()
