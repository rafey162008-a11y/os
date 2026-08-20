"""Constants shared across the application."""

# Order workflow
ORDER_STATUSES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('processing', 'Processing'),
    ('packed', 'Packed'),
    ('shipped', 'Shipped'),
    ('out_for_delivery', 'Out for Delivery'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('returned', 'Returned'),
    ('refunded', 'Refunded'),
    ('failed', 'Failed'),
]

PAYMENT_METHODS = [
    ('cod', 'Cash on Delivery'),
    ('card', 'Credit/Debit Card'),
    ('bank_transfer', 'Bank Transfer'),
    ('wallet', 'Digital Wallet'),
    ('online', 'Online Payment Gateway'),
    ('mobile', 'Mobile Payment'),
]

PAYMENT_STATUSES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('paid', 'Paid'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
    ('partially_refunded', 'Partially Refunded'),
]

SHIPPING_METHODS = [
    ('standard', 'Standard Delivery'),
    ('express', 'Express Delivery'),
    ('pickup', 'Store Pickup'),
]

RETURN_STATUSES = [
    ('requested', 'Requested'),
    ('approved', 'Approved'),
    ('product_returned', 'Product Returned'),
    ('inspected', 'Inspected'),
    ('refunded', 'Refunded'),
    ('replacement', 'Replacement'),
    ('rejected', 'Rejected'),
    ('completed', 'Completed'),
]

DELIVERY_STATUSES = [
    ('not_shipped', 'Not Shipped'),
    ('in_transit', 'In Transit'),
    ('out_for_delivery', 'Out for Delivery'),
    ('delivered', 'Delivered'),
    ('failed', 'Failed'),
]

TICKET_STATUSES = [
    ('open', 'Open'),
    ('replied', 'Replied'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
    ('closed', 'Closed'),
]

TICKET_CATEGORIES = [
    ('general', 'General'),
    ('order', 'Order'),
    ('payment', 'Payment'),
    ('delivery', 'Delivery'),
    ('return', 'Return'),
    ('complaint', 'Complaint'),
]

USER_ROLES = [
    'Super Admin', 'Admin', 'Sales Manager', 'Inventory Manager',
    'Order Manager', 'Delivery Manager', 'Customer Support',
    'Supplier', 'Customer',
]

PERMISSIONS = [
    'manage_products', 'manage_categories', 'manage_brands', 'manage_inventory',
    'manage_suppliers', 'manage_customers', 'manage_orders', 'manage_payments',
    'manage_delivery', 'manage_coupons', 'manage_offers', 'manage_reviews',
    'manage_returns', 'manage_refunds', 'manage_support', 'manage_content',
    'manage_users', 'manage_roles', 'view_reports', 'manage_settings',
    'view_activity_logs', 'manage_notifications',
]

# Badge classes used by the status_badge helper
STATUS_BADGE_MAP = {
    'active': 'success', 'inactive': 'secondary', 'pending': 'warning',
    'confirmed': 'info', 'processing': 'info', 'packed': 'info',
    'shipped': 'primary', 'out_for_delivery': 'primary', 'delivered': 'success',
    'cancelled': 'danger', 'returned': 'warning', 'refunded': 'info',
    'failed': 'danger', 'paid': 'success', 'processing': 'info',
    'partially_refunded': 'warning', 'approved': 'success', 'rejected': 'danger',
    'requested': 'warning', 'product_returned': 'info', 'inspected': 'info',
    'replacement': 'info', 'completed': 'success', 'open': 'primary',
    'replied': 'info', 'in_progress': 'warning', 'resolved': 'success',
    'closed': 'secondary', 'refunded': 'info', 'new': 'primary',
    'ordered': 'info', 'received': 'success', 'in_transit': 'info',
    'not_shipped': 'secondary', 'submitted': 'info', 'none': 'secondary',
    'low': 'danger', 'out_of_stock': 'danger', 'in_stock': 'success',
}
