"""Commerce models: addresses, cart, coupons, orders, payments, shipments,
returns, refunds, reviews, support tickets, loyalty, notifications."""
from datetime import datetime, timedelta
import uuid

from app.extensions import db

# Order workflow statuses
ORDER_STATUSES = [
    'pending', 'confirmed', 'processing', 'packed', 'shipped',
    'out_for_delivery', 'delivered', 'cancelled', 'returned', 'refunded', 'failed'
]

PAYMENT_STATUSES = ['pending', 'processing', 'paid', 'failed', 'refunded', 'partially_refunded']

RETURN_STATUSES = ['requested', 'approved', 'product_returned', 'inspected', 'refunded', 'replacement', 'rejected', 'completed']


def generate_order_number():
    return 'ORD-' + datetime.utcnow().strftime('%Y%m%d') + '-' + uuid.uuid4().hex[:6].upper()


def generate_tracking_number():
    return 'TRK-' + uuid.uuid4().hex[:10].upper()


class Address(db.Model):
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    label = db.Column(db.String(60), default='Home')
    country = db.Column(db.String(80), default='Pakistan')
    province = db.Column(db.String(80))
    city = db.Column(db.String(80), nullable=False)
    area = db.Column(db.String(120))
    street_address = db.Column(db.String(255), nullable=False)
    postal_code = db.Column(db.String(20))
    phone = db.Column(db.String(30))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CartItem(db.Model):
    """Shopping cart items stored per-user (guest carts live in session only)."""
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id', ondelete='SET NULL'), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    saved_for_later = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', lazy='joined')
    variant = db.relationship('ProductVariant', lazy='joined')

    @property
    def unit_price(self):
        if self.variant and self.variant.price:
            return self.variant.price
        return self.product.price

    @property
    def line_total(self):
        try:
            return float(self.unit_price or 0) * self.quantity
        except (TypeError, ValueError):
            return 0.0

    def __repr__(self):
        return f'<CartItem user={self.user_id} product={self.product_id} qty={self.quantity}>'


class Coupon(db.Model):
    __tablename__ = 'coupons'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    discount_type = db.Column(db.String(20), nullable=False, default='percentage')  # percentage | fixed
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    usage_limit = db.Column(db.Integer, default=0)  # 0 = unlimited
    used_count = db.Column(db.Integer, default=0)
    min_purchase = db.Column(db.Numeric(12, 2), default=0)
    max_discount = db.Column(db.Numeric(12, 2), default=0)  # 0 = no cap
    is_active = db.Column(db.Boolean, default=True)
    applies_to = db.Column(db.String(20), default='all')  # all | product | category | brand
    applies_to_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_valid(self):
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.expiry_date and now > self.expiry_date:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    @property
    def expired(self):
        return self.expiry_date is not None and datetime.utcnow() > self.expiry_date

    def __repr__(self):
        return f'<Coupon {self.code}>'


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(40), unique=True, nullable=False, default=generate_order_number, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id', ondelete='SET NULL'), nullable=True)

    subtotal = db.Column(db.Numeric(12, 2), default=0)
    discount = db.Column(db.Numeric(12, 2), default=0)
    tax = db.Column(db.Numeric(12, 2), default=0)
    shipping_charge = db.Column(db.Numeric(12, 2), default=0)
    grand_total = db.Column(db.Numeric(12, 2), default=0)

    shipping_method = db.Column(db.String(50), default='standard')  # standard | express | pickup
    shipping_address = db.Column(db.Text)
    status = db.Column(db.String(30), default='pending', index=True)
    payment_status = db.Column(db.String(30), default='pending')
    notes = db.Column(db.Text)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy='selectin', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    shipment = db.relationship('Shipment', backref='order', uselist=False, cascade='all, delete-orphan')
    returns = db.relationship('ReturnRequest', backref='order', lazy='dynamic', foreign_keys='ReturnRequest.order_id')

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items)

    @property
    def can_cancel(self):
        return self.status in ('pending', 'confirmed', 'processing', 'failed')

    @property
    def can_request_return(self):
        return self.status in ('delivered', 'returned')

    @property
    def customer_name(self):
        return self.customer.full_name if self.customer else ''

    def __repr__(self):
        return f'<Order {self.order_number}>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    variant_label = db.Column(db.String(120))
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Numeric(12, 2), default=0)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)
    review_status = db.Column(db.String(20), default='none')  # none | submitted

    @property
    def image(self):
        if self.product and self.product.main_image:
            return self.product.main_image
        return None


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    payment_reference = db.Column(db.String(50), unique=True, nullable=False,
                                  default=lambda: 'PAY-' + uuid.uuid4().hex[:12].upper())
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    transaction_id = db.Column(db.String(100), index=True)
    method = db.Column(db.String(50), nullable=False)  # cod | card | bank_transfer | wallet | online | mobile
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(30), default='pending', index=True)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    failure_reason = db.Column(db.String(255))
    refund_info = db.Column(db.String(255))
    # NEVER store card numbers - only a token reference
    card_token = db.Column(db.String(100), nullable=True, comment='Tokenized card reference only')

    @property
    def method_display(self):
        return dict(cod='Cash on Delivery', card='Credit/Debit Card', bank_transfer='Bank Transfer',
                    wallet='Digital Wallet', online='Online Gateway', mobile='Mobile Payment') \
            .get(self.method, self.method.title())


class Shipment(db.Model):
    __tablename__ = 'shipments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, unique=True)
    tracking_number = db.Column(db.String(60), default=generate_tracking_number, index=True)
    shipping_company = db.Column(db.String(100), default='ShopSphere Logistics')
    delivery_status = db.Column(db.String(40), default='not_shipped')  # not_shipped | in_transit | out_for_delivery | delivered | failed
    expected_delivery = db.Column(db.Date)
    delivered_at = db.Column(db.DateTime)
    delivery_area = db.Column(db.String(120))
    delivery_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReturnRequest(db.Model):
    __tablename__ = 'returns'

    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(40), unique=True, nullable=False,
                              default=lambda: 'RET-' + uuid.uuid4().hex[:10].upper())
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='SET NULL'))
    reason = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    evidence_images = db.Column(db.Text)  # comma-separated file names
    status = db.Column(db.String(30), default='requested', index=True)
    refund_amount = db.Column(db.Numeric(12, 2))
    refund_method = db.Column(db.String(50))
    admin_notes = db.Column(db.Text)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship('Product', lazy='joined')
    refund = db.relationship('Refund', backref='return_request', uselist=False, cascade='all, delete-orphan')


class Refund(db.Model):
    __tablename__ = 'refunds'

    id = db.Column(db.Integer, primary_key=True)
    refund_number = db.Column(db.String(40), unique=True, nullable=False,
                              default=lambda: 'RFD-' + uuid.uuid4().hex[:10].upper())
    return_id = db.Column(db.Integer, db.ForeignKey('returns.id', ondelete='CASCADE'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(50))
    status = db.Column(db.String(30), default='processing')  # processing | completed | failed
    transaction_id = db.Column(db.String(100))
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(150))
    comment = db.Column(db.Text)
    image = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending', index=True)  # pending | approved | rejected
    verified_purchase = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('product_id', 'customer_id', name='uq_review_product_customer'),
    )


class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False,
                              default=lambda: 'SUP-' + uuid.uuid4().hex[:8].upper())
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='general')  # general | order | payment | delivery | return | complaint
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low | normal | high | urgent
    status = db.Column(db.String(20), default='open', index=True)  # open | replied | in_progress | resolved | closed
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    replies = db.relationship('SupportReply', backref='ticket', lazy='selectin', cascade='all, delete-orphan')


class SupportReply(db.Model):
    __tablename__ = 'support_replies'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    message = db.Column(db.Text, nullable=False)
    is_staff = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LoyaltyTransaction(db.Model):
    __tablename__ = 'loyalty_points'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)  # positive = earn, negative = redeem
    reason = db.Column(db.String(150))
    reference_type = db.Column(db.String(50))  # purchase | review | referral | redeem
    reference_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(255))
    type = db.Column(db.String(40), default='info')  # info | order | payment | offer | wishlist | system
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
