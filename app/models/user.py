"""User, role and permission models with role-based access control."""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

# Association table: many-to-many users <-> roles
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
)


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    permissions = db.relationship('Permission', backref='role', lazy='joined')
    users = db.relationship('User', secondary=user_roles, back_populates='roles', lazy='selectin')

    def __repr__(self):
        return f'<Role {self.name}>'


class Permission(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g. 'manage_products'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('role_id', 'name', name='uq_role_permission'),)


class User(UserMixin, db.Model):
    """A single user table used for both customers and staff (role-based)."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_staff = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = db.relationship('Role', secondary=user_roles, back_populates='users', lazy='selectin')

    # Customer-specific relationships
    addresses = db.relationship('Address', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='customer', lazy='dynamic', foreign_keys='Order.customer_id')
    reviews = db.relationship('Review', backref='customer', lazy='dynamic', foreign_keys='Review.customer_id')
    return_requests = db.relationship('ReturnRequest', backref='customer', lazy='dynamic', foreign_keys='ReturnRequest.customer_id')
    support_tickets = db.relationship('SupportTicket', backref='customer', lazy='dynamic', foreign_keys='SupportTicket.customer_id')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    loyalty_transactions = db.relationship('LoyaltyTransaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # --- Password helpers ---
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Role helpers ---
    def has_role(self, role_name):
        return any(r.name == role_name for r in self.roles)

    def has_permission(self, perm_name):
        if self.has_role('Super Admin'):
            return True
        for r in self.roles:
            for p in r.permissions:
                if p.name == perm_name:
                    return True
        return False

    @property
    def is_customer(self):
        return not self.is_staff

    @property
    def display_roles(self):
        return ', '.join(r.name for r in self.roles) if self.roles else ('Customer' if not self.is_staff else 'Staff')

    @property
    def loyalty_balance(self):
        from sqlalchemy import func
        total = db.session.query(func.coalesce(func.sum(LoyaltyTransaction.points), 0)) \
            .filter(LoyaltyTransaction.user_id == self.id) \
            .scalar()
        return int(total or 0)

    def __repr__(self):
        return f'<User {self.email}>'


# Imported here to avoid circular imports for relationship definitions
from app.models.commerce import LoyaltyTransaction  # noqa: E402
