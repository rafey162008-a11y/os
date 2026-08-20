"""Database models package. Import all models so SQLAlchemy metadata is complete."""
from app.models.user import User, Role, Permission, user_roles
from app.models.content import Setting, Banner, NewsletterSubscriber, PageContent
from app.models.catalog import (
    Category, Brand, Product, ProductImage, ProductVariant,
    ProductSpecification, ProductFeature, Wishlist
)
from app.models.commerce import (
    Address, CartItem, Coupon, Order, OrderItem, Payment,
    Shipment, ReturnRequest, Refund, Review, SupportTicket,
    SupportReply, LoyaltyTransaction, Notification
)
from app.models.business import (
    Supplier, SupplierProduct, Purchase, PurchaseItem,
    InventoryMovement, ActivityLog
)

__all__ = [
    'User', 'Role', 'Permission', 'user_roles',
    'Setting', 'Banner', 'NewsletterSubscriber', 'PageContent',
    'Category', 'Brand', 'Product', 'ProductImage', 'ProductVariant',
    'ProductSpecification', 'ProductFeature', 'Wishlist',
    'Address', 'CartItem', 'Coupon', 'Order', 'OrderItem', 'Payment',
    'Shipment', 'ReturnRequest', 'Refund', 'Review', 'SupportTicket',
    'SupportReply', 'LoyaltyTransaction', 'Notification',
    'Supplier', 'SupplierProduct', 'Purchase', 'PurchaseItem',
    'InventoryMovement', 'ActivityLog',
]
