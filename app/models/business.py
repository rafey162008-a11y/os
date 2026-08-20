"""Business models: suppliers, purchases, inventory movements, activity logs."""
from datetime import datetime

from app.extensions import db


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120), index=True)
    address = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    supplied_products = db.relationship('SupplierProduct', backref='supplier', lazy='dynamic',
                                        cascade='all, delete-orphan')
    purchases = db.relationship('Purchase', backref='supplier', lazy='dynamic', foreign_keys='Purchase.supplier_id')

    @property
    def total_purchases(self):
        from sqlalchemy import func
        return db.session.query(func.coalesce(func.sum(Purchase.total_amount), 0)) \
            .filter(Purchase.supplier_id == self.id).scalar() or 0

    @property
    def outstanding_balance(self):
        return self.total_purchases - (self.total_paid or 0)

    @property
    def total_paid(self):
        from sqlalchemy import func
        return db.session.query(func.coalesce(func.sum(Purchase.amount_paid), 0)) \
            .filter(Purchase.supplier_id == self.id).scalar() or 0

    def __repr__(self):
        return f'<Supplier {self.name}>'


class SupplierProduct(db.Model):
    __tablename__ = 'supplier_products'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    supply_price = db.Column(db.Numeric(12, 2))
    lead_time_days = db.Column(db.Integer, default=0)

    product = db.relationship('Product', lazy='joined')

    __table_args__ = (db.UniqueConstraint('supplier_id', 'product_id', name='uq_supplier_product'),)


class Purchase(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    purchase_number = db.Column(db.String(40), unique=True, nullable=False,
                                default=lambda: 'PUR-' + datetime.utcnow().strftime('%Y%m%d-%H%M%S'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False, index=True)
    reference = db.Column(db.String(100))
    total_amount = db.Column(db.Numeric(12, 2), default=0)
    amount_paid = db.Column(db.Numeric(12, 2), default=0)
    status = db.Column(db.String(20), default='received')  # ordered | received | cancelled
    notes = db.Column(db.Text)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('PurchaseItem', backref='purchase', lazy='selectin', cascade='all, delete-orphan')

    @property
    def balance(self):
        return float(self.total_amount or 0) - float(self.amount_paid or 0)


class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_name = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=0)
    unit_cost = db.Column(db.Numeric(12, 2), default=0)
    line_total = db.Column(db.Numeric(12, 2), default=0)

    product = db.relationship('Product', lazy='joined')


class InventoryMovement(db.Model):
    __tablename__ = 'inventory_movements'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    quantity_change = db.Column(db.Integer, nullable=False)  # + stock in, - stock out
    reason = db.Column(db.String(120), nullable=False)  # sale | purchase | return | adjustment | cancellation
    reference_type = db.Column(db.String(40))
    reference_id = db.Column(db.Integer)
    stock_after = db.Column(db.Integer)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', lazy='joined')


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    user_name = db.Column(db.String(120))
    action = db.Column(db.String(80), nullable=False, index=True)  # create | update | delete | login | logout | ...
    entity = db.Column(db.String(80))  # product | order | user ...
    entity_id = db.Column(db.Integer)
    description = db.Column(db.String(255))
    ip_address = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<ActivityLog {self.action} {self.entity}>'
