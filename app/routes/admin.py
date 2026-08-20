"""Admin panel routes: dashboard, catalog, commerce, business, content, system."""
import csv
import io
from datetime import datetime, timedelta
from io import BytesIO

from flask import (Blueprint, render_template, redirect, url_for, flash, abort,
                   request, send_file, Response, current_app)
from flask_login import current_user
from sqlalchemy import desc, func, and_

from app.extensions import db
from app.models.catalog import (Category, Brand, Product, ProductImage,
                                ProductVariant, ProductSpecification, ProductFeature)
from app.models.user import User, Role, Permission
from app.models.commerce import (Order, OrderItem, Payment, Shipment, ReturnRequest,
                                 Refund, Review, SupportTicket, SupportReply,
                                 Coupon, Notification, Address, CartItem)
from app.models.business import Supplier, SupplierProduct, Purchase, PurchaseItem, InventoryMovement, ActivityLog
from app.models.content import Setting, Banner, NewsletterSubscriber, PageContent
from app.forms.admin_forms import (CategoryForm, BrandForm, ProductForm, VariantForm,
                                   SpecificationForm, SupplierForm, PurchaseForm,
                                   CouponForm, UserForm, SettingsForm)
from app.utils.decorators import admin_required, permission_required
from app.utils.helpers import (slugify, unique_slug, unique_sku, save_upload,
                               delete_upload, update_settings_cache)
from app.utils.activity import log_action
from app.services.order_service import update_order_status
from app.utils.constants import (ORDER_STATUSES, PAYMENT_STATUSES, SHIPPING_METHODS,
                                 RETURN_STATUSES, DELIVERY_STATUSES, TICKET_STATUSES,
                                 PERMISSIONS, USER_ROLES)
from app.utils.pdf import generate_invoice_pdf

admin_bp = Blueprint('admin', __name__)


# ---------------------------------------------------------------------------
# Helpers for exports
# ---------------------------------------------------------------------------
def _csv_response(rows, filename):
    si = io.StringIO()
    writer = csv.writer(si)
    for row in rows:
        writer.writerow(row)
    return Response(si.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


def _excel_response(rows, filename, sheet='Report'):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for row in rows:
        ws.append(list(row))
    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(out,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)


def _pdf_table_response(title, header, rows, filename):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    elems = [Paragraph(title, styles['Title']), Spacer(1, 8 * mm)]
    data = [header] + [list(r) for r in rows]
    table = Table(data, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elems.append(table)
    doc.build(elems)
    out.seek(0)
    return send_file(out, mimetype='application/pdf', as_attachment=True, download_name=filename)


def _populate_product_form(form, product=None):
    """Fill category/brand/subcategory choices for the product form."""
    form.category_id.choices = [(0, 'Select Category')] + [
        (c.id, c.name) for c in Category.query.filter_by(parent_id=None).order_by(Category.name).all()]
    form.subcategory_id.choices = [(0, 'None')] + [
        (c.id, c.name) for c in Category.query.filter(Category.parent_id.isnot(None)).order_by(Category.name).all()]
    form.brand_id.choices = [(0, 'Select Brand')] + [
        (b.id, b.name) for b in Brand.query.order_by(Brand.name).all()]
    if product:
        form.category_id.data = product.category_id or 0
        form.subcategory_id.data = product.subcategory_id or 0
        form.brand_id.data = product.brand_id or 0


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = datetime.utcnow().date()
    start_month = today.replace(day=1)
    total_products = Product.query.count()
    low_stock = Product.query.filter(Product.stock_quantity <= Product.min_stock_level,
                                     Product.stock_quantity > 0).count()
    out_of_stock = Product.query.filter(Product.stock_quantity <= 0).count()
    total_customers = User.query.filter_by(is_staff=False).count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter(Order.status.in_(['pending', 'confirmed', 'processing'])).count()
    month_orders = Order.query.filter(Order.placed_at >= start_month).count()
    month_revenue = db.session.query(func.coalesce(func.sum(Order.grand_total), 0)).filter(
        Order.placed_at >= start_month, Order.payment_status == 'paid').scalar() or 0
    open_tickets = SupportTicket.query.filter(SupportTicket.status.in_(['open', 'replied', 'in_progress'])).count()
    pending_reviews = Review.query.filter_by(status='pending').count()
    pending_returns = ReturnRequest.query.filter(ReturnRequest.status.in_(['requested', 'approved', 'product_returned', 'inspected'])).count()
    recent_orders = Order.query.order_by(desc(Order.placed_at)).limit(8).all()
    recent_activity = ActivityLog.query.order_by(desc(ActivityLog.created_at)).limit(10).all()
    # Sales chart data (last 7 days)
    days = []
    sales = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        days.append(d.strftime('%a'))
        rev = db.session.query(func.coalesce(func.sum(Order.grand_total), 0)).filter(
            func.date(Order.placed_at) == d, Order.payment_status == 'paid').scalar() or 0
        sales.append(float(rev))
    return render_template('admin/dashboard.html',
                           total_products=total_products, low_stock=low_stock, out_of_stock=out_of_stock,
                           total_customers=total_customers, total_orders=total_orders,
                           pending_orders=pending_orders, month_orders=month_orders,
                           month_revenue=month_revenue, open_tickets=open_tickets,
                           pending_reviews=pending_reviews, pending_returns=pending_returns,
                           recent_orders=recent_orders, recent_activity=recent_activity,
                           chart_days=days, chart_sales=sales)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
@admin_bp.route('/products')
@permission_required('manage_products')
def products():
    page = request.args.get('page', 1, type=int)
    q = (request.args.get('q') or '').strip()
    status = request.args.get('status', '')
    cat = request.args.get('category', type=int)
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%'))
    if status:
        query = query.filter_by(status=status)
    if cat:
        query = query.filter_by(category_id=cat)
    items = query.order_by(desc(Product.created_at)).paginate(page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    return render_template('admin/products.html', products=items, categories=categories,
                           q=q, status=status, cat=cat)


@admin_bp.route('/products/new', methods=['GET', 'POST'])
@permission_required('manage_products')
def product_new():
    form = ProductForm()
    _populate_product_form(form)
    if form.validate_on_submit():
        image = None
        if form.main_image.data:
            image = save_upload(form.main_image.data, 'products')
        product = Product(
            name=form.name.data,
            slug=unique_slug(Product, form.name.data),
            sku=form.sku.data or unique_sku(Product),
            category_id=form.category_id.data or None,
            subcategory_id=form.subcategory_id.data or None,
            brand_id=form.brand_id.data or None,
            main_image=image,
            video_url=form.video_url.data,
            short_description=form.short_description.data,
            description=form.description.data,
            price=form.price.data,
            old_price=form.old_price.data,
            cost_price=form.cost_price.data,
            stock_quantity=form.stock_quantity.data or 0,
            min_stock_level=form.min_stock_level.data or 0,
            colors=form.colors.data,
            sizes=form.sizes.data,
            warranty_info=form.warranty_info.data,
            return_policy=form.return_policy.data,
            shipping_info=form.shipping_info.data,
            condition=form.condition.data,
            is_featured=form.is_featured.data,
            is_bestseller=form.is_bestseller.data,
            is_new_arrival=form.is_new_arrival.data,
            is_flash_sale=form.is_flash_sale.data,
            is_recommended=form.is_recommended.data,
            status=form.status.data,
        )
        db.session.add(product)
        db.session.commit()
        log_action('create', 'product', product.id, f'Created product {product.name}')
        flash('Product created successfully.', 'success')
        return redirect(url_for('admin.products'))
    return render_template('admin/product_form.html', form=form, product=None, title='New Product')


@admin_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_products')
def product_edit(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    form = ProductForm(obj=product)
    _populate_product_form(form, product)
    if form.validate_on_submit():
        if form.main_image.data:
            if product.main_image:
                delete_upload(product.main_image)
            product.main_image = save_upload(form.main_image.data, 'products')
        product.name = form.name.data
        product.category_id = form.category_id.data or None
        product.subcategory_id = form.subcategory_id.data or None
        product.brand_id = form.brand_id.data or None
        product.video_url = form.video_url.data
        product.short_description = form.short_description.data
        product.description = form.description.data
        product.price = form.price.data
        product.old_price = form.old_price.data
        product.cost_price = form.cost_price.data
        product.stock_quantity = form.stock_quantity.data or 0
        product.min_stock_level = form.min_stock_level.data or 0
        product.colors = form.colors.data
        product.sizes = form.sizes.data
        product.warranty_info = form.warranty_info.data
        product.return_policy = form.return_policy.data
        product.shipping_info = form.shipping_info.data
        product.condition = form.condition.data
        product.is_featured = form.is_featured.data
        product.is_bestseller = form.is_bestseller.data
        product.is_new_arrival = form.is_new_arrival.data
        product.is_flash_sale = form.is_flash_sale.data
        product.is_recommended = form.is_recommended.data
        product.status = form.status.data
        db.session.commit()
        log_action('update', 'product', product.id, f'Updated product {product.name}')
        flash('Product updated successfully.', 'success')
        return redirect(url_for('admin.products'))
    return render_template('admin/product_form.html', form=form, product=product, title='Edit Product')


@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@permission_required('manage_products')
def product_delete(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if product.main_image:
        delete_upload(product.main_image)
    for img in product.images:
        delete_upload(img.image)
    db.session.delete(product)
    db.session.commit()
    log_action('delete', 'product', product_id, f'Deleted product {product.name}')
    flash('Product deleted.', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/<int:product_id>/images', methods=['GET', 'POST'])
@permission_required('manage_products')
def product_images(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if request.method == 'POST':
        files = request.files.getlist('images')
        order = product.images.count()
        for f in files:
            path = save_upload(f, 'products')
            if path:
                db.session.add(ProductImage(product_id=product.id, image=path, display_order=order))
                order += 1
        db.session.commit()
        flash('Images uploaded.', 'success')
        return redirect(url_for('admin.product_images', product_id=product.id))
    return render_template('admin/product_images.html', product=product)


@admin_bp.route('/products/<int:product_id>/images/<int:image_id>/delete', methods=['POST'])
@permission_required('manage_products')
def product_image_delete(product_id, image_id):
    img = db.session.get(ProductImage, image_id) or abort(404)
    delete_upload(img.image)
    db.session.delete(img)
    db.session.commit()
    flash('Image removed.', 'success')
    return redirect(url_for('admin.product_images', product_id=product_id))


@admin_bp.route('/products/<int:product_id>/variants', methods=['GET', 'POST'])
@permission_required('manage_products')
def product_variants(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    form = VariantForm()
    if form.validate_on_submit():
        db.session.add(ProductVariant(
            product_id=product.id, name=form.name.data, sku=form.sku.data,
            price=form.price.data, stock_quantity=form.stock_quantity.data or 0,
            attributes=form.attributes.data))
        db.session.commit()
        flash('Variant added.', 'success')
        return redirect(url_for('admin.product_variants', product_id=product.id))
    return render_template('admin/product_variants.html', product=product, form=form)


@admin_bp.route('/products/<int:product_id>/variants/<int:variant_id>/delete', methods=['POST'])
@permission_required('manage_products')
def product_variant_delete(product_id, variant_id):
    v = db.session.get(ProductVariant, variant_id) or abort(404)
    db.session.delete(v)
    db.session.commit()
    flash('Variant removed.', 'success')
    return redirect(url_for('admin.product_variants', product_id=product_id))


@admin_bp.route('/products/<int:product_id>/specs', methods=['POST'])
@permission_required('manage_products')
def product_spec_add(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    form = SpecificationForm()
    if form.validate_on_submit():
        db.session.add(ProductSpecification(product_id=product.id, label=form.label.data, value=form.value.data))
        db.session.commit()
        flash('Specification added.', 'success')
    return redirect(url_for('admin.product_edit', product_id=product.id))


@admin_bp.route('/products/<int:product_id>/specs/<int:spec_id>/delete', methods=['POST'])
@permission_required('manage_products')
def product_spec_delete(product_id, spec_id):
    s = db.session.get(ProductSpecification, spec_id) or abort(404)
    db.session.delete(s)
    db.session.commit()
    flash('Specification removed.', 'success')
    return redirect(url_for('admin.product_edit', product_id=product_id))


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@admin_bp.route('/categories')
@permission_required('manage_categories')
def categories():
    cats = Category.query.filter_by(parent_id=None).order_by(Category.display_order, Category.name).all()
    return render_template('admin/categories.html', categories=cats)


@admin_bp.route('/categories/new', methods=['GET', 'POST'])
@permission_required('manage_categories')
def category_new():
    form = CategoryForm()
    form.parent_id.choices = [(0, 'None (Top Level)')] + [
        (c.id, c.name) for c in Category.query.filter_by(parent_id=None).order_by(Category.name).all()]
    if form.validate_on_submit():
        image = save_upload(form.image.data, 'categories') if form.image.data else None
        cat = Category(name=form.name.data, slug=unique_slug(Category, form.name.data),
                       description=form.description.data, parent_id=form.parent_id.data or None,
                       image=image, status=form.status.data, display_order=form.display_order.data or 0)
        db.session.add(cat)
        db.session.commit()
        log_action('create', 'category', cat.id, f'Created category {cat.name}')
        flash('Category created.', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/category_form.html', form=form, category=None, title='New Category')


@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_categories')
def category_edit(category_id):
    cat = db.session.get(Category, category_id) or abort(404)
    form = CategoryForm(obj=cat)
    form.parent_id.choices = [(0, 'None (Top Level)')] + [
        (c.id, c.name) for c in Category.query.filter(Category.parent_id.is_(None), Category.id != cat.id).order_by(Category.name).all()]
    if form.validate_on_submit():
        if form.image.data:
            if cat.image:
                delete_upload(cat.image)
            cat.image = save_upload(form.image.data, 'categories')
        cat.name = form.name.data
        cat.description = form.description.data
        cat.parent_id = form.parent_id.data or None
        cat.status = form.status.data
        cat.display_order = form.display_order.data or 0
        db.session.commit()
        log_action('update', 'category', cat.id, f'Updated category {cat.name}')
        flash('Category updated.', 'success')
        return redirect(url_for('admin.categories'))
    form.parent_id.data = cat.parent_id or 0
    return render_template('admin/category_form.html', form=form, category=cat, title='Edit Category')


@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@permission_required('manage_categories')
def category_delete(category_id):
    cat = db.session.get(Category, category_id) or abort(404)
    if cat.products.count() or cat.subcategories.count():
        flash('Cannot delete category with products or subcategories.', 'danger')
        return redirect(url_for('admin.categories'))
    if cat.image:
        delete_upload(cat.image)
    db.session.delete(cat)
    db.session.commit()
    log_action('delete', 'category', category_id, f'Deleted category {cat.name}')
    flash('Category deleted.', 'success')
    return redirect(url_for('admin.categories'))


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------
@admin_bp.route('/brands')
@permission_required('manage_brands')
def brands():
    brands = Brand.query.order_by(Brand.name).all()
    return render_template('admin/brands.html', brands=brands)


@admin_bp.route('/brands/new', methods=['GET', 'POST'])
@permission_required('manage_brands')
def brand_new():
    form = BrandForm()
    if form.validate_on_submit():
        logo = save_upload(form.logo.data, 'brands') if form.logo.data else None
        brand = Brand(name=form.name.data, slug=unique_slug(Brand, form.name.data),
                      description=form.description.data, logo=logo, status=form.status.data)
        db.session.add(brand)
        db.session.commit()
        log_action('create', 'brand', brand.id, f'Created brand {brand.name}')
        flash('Brand created.', 'success')
        return redirect(url_for('admin.brands'))
    return render_template('admin/brand_form.html', form=form, brand=None, title='New Brand')


@admin_bp.route('/brands/<int:brand_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_brands')
def brand_edit(brand_id):
    brand = db.session.get(Brand, brand_id) or abort(404)
    form = BrandForm(obj=brand)
    if form.validate_on_submit():
        if form.logo.data:
            if brand.logo:
                delete_upload(brand.logo)
            brand.logo = save_upload(form.logo.data, 'brands')
        brand.name = form.name.data
        brand.description = form.description.data
        brand.status = form.status.data
        db.session.commit()
        log_action('update', 'brand', brand.id, f'Updated brand {brand.name}')
        flash('Brand updated.', 'success')
        return redirect(url_for('admin.brands'))
    return render_template('admin/brand_form.html', form=form, brand=brand, title='Edit Brand')


@admin_bp.route('/brands/<int:brand_id>/delete', methods=['POST'])
@permission_required('manage_brands')
def brand_delete(brand_id):
    brand = db.session.get(Brand, brand_id) or abort(404)
    if brand.products.count():
        flash('Cannot delete brand with products.', 'danger')
        return redirect(url_for('admin.brands'))
    if brand.logo:
        delete_upload(brand.logo)
    db.session.delete(brand)
    db.session.commit()
    log_action('delete', 'brand', brand_id, f'Deleted brand {brand.name}')
    flash('Brand deleted.', 'success')
    return redirect(url_for('admin.brands'))


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
@admin_bp.route('/inventory')
@permission_required('manage_inventory')
def inventory():
    page = request.args.get('page', 1, type=int)
    q = (request.args.get('q') or '').strip()
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%'))
    items = query.order_by(Product.stock_quantity.asc()).paginate(page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/inventory.html', products=items, q=q)


@admin_bp.route('/inventory/adjust/<int:product_id>', methods=['GET', 'POST'])
@permission_required('manage_inventory')
def inventory_adjust(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if request.method == 'POST':
        try:
            change = int(request.form.get('change', 0))
        except ValueError:
            change = 0
        reason = request.form.get('reason', 'adjustment')
        note = request.form.get('note', '')
        if change != 0:
            product.stock_quantity = (product.stock_quantity or 0) + change
            db.session.add(InventoryMovement(
                product_id=product.id, user_id=current_user.id, quantity_change=change,
                reason=reason, reference_type='adjustment', reference_id=product.id,
                stock_after=product.stock_quantity, notes=note))
            db.session.commit()
            log_action('update', 'inventory', product.id, f'Adjusted stock of {product.name} by {change}')
            flash('Stock adjusted.', 'success')
        return redirect(url_for('admin.inventory'))
    return render_template('admin/inventory_adjust.html', product=product)


@admin_bp.route('/inventory/movements')
@permission_required('manage_inventory')
def inventory_movements():
    page = request.args.get('page', 1, type=int)
    items = InventoryMovement.query.order_by(desc(InventoryMovement.created_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/inventory_movements.html', movements=items)


# ---------------------------------------------------------------------------
# Suppliers & Purchases
# ---------------------------------------------------------------------------
@admin_bp.route('/suppliers')
@permission_required('manage_suppliers')
def suppliers():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('admin/suppliers.html', suppliers=suppliers)


@admin_bp.route('/suppliers/new', methods=['GET', 'POST'])
@permission_required('manage_suppliers')
def supplier_new():
    form = SupplierForm()
    if form.validate_on_submit():
        s = Supplier(name=form.name.data, company=form.company.data, phone=form.phone.data,
                     email=form.email.data, address=form.address.data, status=form.status.data)
        db.session.add(s)
        db.session.commit()
        log_action('create', 'supplier', s.id, f'Created supplier {s.name}')
        flash('Supplier created.', 'success')
        return redirect(url_for('admin.suppliers'))
    return render_template('admin/supplier_form.html', form=form, supplier=None, title='New Supplier')


@admin_bp.route('/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_suppliers')
def supplier_edit(supplier_id):
    s = db.session.get(Supplier, supplier_id) or abort(404)
    form = SupplierForm(obj=s)
    if form.validate_on_submit():
        s.name = form.name.data
        s.company = form.company.data
        s.phone = form.phone.data
        s.email = form.email.data
        s.address = form.address.data
        s.status = form.status.data
        db.session.commit()
        log_action('update', 'supplier', s.id, f'Updated supplier {s.name}')
        flash('Supplier updated.', 'success')
        return redirect(url_for('admin.suppliers'))
    return render_template('admin/supplier_form.html', form=form, supplier=s, title='Edit Supplier')


@admin_bp.route('/suppliers/<int:supplier_id>/delete', methods=['POST'])
@permission_required('manage_suppliers')
def supplier_delete(supplier_id):
    s = db.session.get(Supplier, supplier_id) or abort(404)
    db.session.delete(s)
    db.session.commit()
    log_action('delete', 'supplier', supplier_id, f'Deleted supplier {s.name}')
    flash('Supplier deleted.', 'success')
    return redirect(url_for('admin.suppliers'))


@admin_bp.route('/purchases')
@permission_required('manage_suppliers')
def purchases():
    page = request.args.get('page', 1, type=int)
    items = Purchase.query.order_by(desc(Purchase.purchased_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/purchases.html', purchases=items)


@admin_bp.route('/purchases/new', methods=['GET', 'POST'])
@permission_required('manage_suppliers')
def purchase_new():
    form = PurchaseForm()
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    form.product_id.choices = [(p.id, p.name) for p in Product.query.order_by(Product.name).all()]
    if form.validate_on_submit():
        product = db.session.get(Product, form.product_id.data) or abort(404)
        qty = form.quantity.data or 0
        unit = form.unit_cost.data or 0
        line_total = round(qty * float(unit), 2)
        amount_paid = form.amount_paid.data or 0
        purchase = Purchase(supplier_id=form.supplier_id.data, reference=form.reference.data,
                            total_amount=line_total, amount_paid=amount_paid,
                            status='received', notes=form.notes.data)
        db.session.add(purchase)
        db.session.flush()
        db.session.add(PurchaseItem(purchase_id=purchase.id, product_id=product.id,
                                    product_name=product.name, quantity=qty,
                                    unit_cost=unit, line_total=line_total))
        # increase stock
        product.stock_quantity = (product.stock_quantity or 0) + qty
        db.session.add(InventoryMovement(product_id=product.id, user_id=current_user.id,
                                         quantity_change=qty, reason='purchase',
                                         reference_type='purchase', reference_id=purchase.id,
                                         stock_after=product.stock_quantity))
        db.session.commit()
        log_action('create', 'purchase', purchase.id, f'Recorded purchase from supplier #{form.supplier_id.data}')
        flash('Purchase recorded and stock updated.', 'success')
        return redirect(url_for('admin.purchases'))
    return render_template('admin/purchase_form.html', form=form, title='Record Purchase')


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
@admin_bp.route('/orders')
@permission_required('manage_orders')
def orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    q = (request.args.get('q') or '').strip()
    query = Order.query
    if status:
        query = query.filter_by(status=status)
    if q:
        query = query.filter(Order.order_number.ilike(f'%{q}%'))
    items = query.order_by(desc(Order.placed_at)).paginate(page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/orders.html', orders=items, status=status, q=q,
                           order_statuses=ORDER_STATUSES)


@admin_bp.route('/orders/<int:order_id>')
@permission_required('manage_orders')
def order_detail(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    return render_template('admin/order_detail.html', order=order,
                           order_statuses=ORDER_STATUSES, payment_statuses=PAYMENT_STATUSES,
                           shipping_methods=SHIPPING_METHODS, delivery_statuses=DELIVERY_STATUSES)


@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@permission_required('manage_orders')
def order_update_status(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    new_status = request.form.get('status')
    note = request.form.get('note', '')
    ok, msg = update_order_status(order, new_status, actor=current_user, note=note)
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('admin.order_detail', order_id=order.id))


@admin_bp.route('/orders/<int:order_id>/invoice')
@permission_required('manage_orders')
def order_invoice(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    from app.utils.helpers import settings_value
    pdf = generate_invoice_pdf(order, store_name=settings_value('store_name', 'ShopSphere'))
    return send_file(BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                     download_name=f'invoice-{order.order_number}.pdf')


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
@admin_bp.route('/payments')
@permission_required('manage_payments')
def payments():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Payment.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(desc(Payment.payment_date)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/payments.html', payments=items, status=status,
                           payment_statuses=PAYMENT_STATUSES)


@admin_bp.route('/payments/<int:payment_id>/status', methods=['POST'])
@permission_required('manage_payments')
def payment_update_status(payment_id):
    payment = db.session.get(Payment, payment_id) or abort(404)
    payment.status = request.form.get('status', payment.status)
    db.session.commit()
    flash('Payment status updated.', 'success')
    return redirect(url_for('admin.payments'))


# ---------------------------------------------------------------------------
# Delivery / Shipments
# ---------------------------------------------------------------------------
@admin_bp.route('/deliveries')
@permission_required('manage_delivery')
def deliveries():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Shipment.query
    if status:
        query = query.filter_by(delivery_status=status)
    items = query.order_by(desc(Shipment.created_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/deliveries.html', deliveries=items, status=status,
                           delivery_statuses=DELIVERY_STATUSES)


@admin_bp.route('/deliveries/<int:order_id>/update', methods=['POST'])
@permission_required('manage_delivery')
def delivery_update(order_id):
    shipment = Shipment.query.filter_by(order_id=order_id).first() or abort(404)
    shipment.delivery_status = request.form.get('delivery_status', shipment.delivery_status)
    shipment.tracking_number = request.form.get('tracking_number') or shipment.tracking_number
    shipment.shipping_company = request.form.get('shipping_company') or shipment.shipping_company
    exp = request.form.get('expected_delivery')
    if exp:
        try:
            shipment.expected_delivery = datetime.strptime(exp, '%Y-%m-%d').date()
        except ValueError:
            pass
    shipment.delivery_notes = request.form.get('delivery_notes', '')
    if shipment.delivery_status == 'delivered':
        shipment.delivered_at = datetime.utcnow()
        order = shipment.order
        if order and order.status not in ('delivered', 'cancelled', 'returned', 'refunded'):
            update_order_status(order, 'delivered', actor=current_user, note='Marked delivered by delivery manager')
    db.session.commit()
    flash('Shipment updated.', 'success')
    return redirect(url_for('admin.deliveries'))


# ---------------------------------------------------------------------------
# Returns & Refunds
# ---------------------------------------------------------------------------
@admin_bp.route('/returns')
@permission_required('manage_returns')
def returns():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = ReturnRequest.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(desc(ReturnRequest.requested_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/returns.html', returns=items, status=status,
                           return_statuses=RETURN_STATUSES)


@admin_bp.route('/returns/<int:return_id>', methods=['GET', 'POST'])
@permission_required('manage_returns')
def return_detail(return_id):
    ret = db.session.get(ReturnRequest, return_id) or abort(404)
    if request.method == 'POST':
        new_status = request.form.get('status')
        ret.status = new_status
        ret.admin_notes = request.form.get('admin_notes', ret.admin_notes)
        refund_amount = request.form.get('refund_amount')
        if refund_amount:
            try:
                ret.refund_amount = float(refund_amount)
            except ValueError:
                pass
        # restore stock when product returned
        if new_status in ('product_returned', 'inspected', 'refunded', 'completed'):
            product = ret.product
            if product:
                # find order item qty
                order_item = OrderItem.query.filter_by(order_id=ret.order_id, product_id=ret.product_id).first()
                qty = order_item.quantity if order_item else 1
                product.stock_quantity = (product.stock_quantity or 0) + qty
                db.session.add(InventoryMovement(product_id=product.id, user_id=current_user.id,
                                                 quantity_change=qty, reason='return',
                                                 reference_type='return', reference_id=ret.id,
                                                 stock_after=product.stock_quantity))
        # create refund record
        if new_status == 'refunded' and not ret.refund:
            refund = Refund(return_id=ret.id, order_id=ret.order_id,
                            amount=ret.refund_amount or 0, method=ret.refund_method or 'original',
                            status='completed')
            db.session.add(refund)
            order = ret.order
            if order:
                order.status = 'refunded'
        db.session.commit()
        log_action('update', 'return', ret.id, f'Updated return {ret.return_number} to {new_status}')
        flash('Return updated.', 'success')
        return redirect(url_for('admin.returns'))
    return render_template('admin/return_detail.html', ret=ret, return_statuses=RETURN_STATUSES)


@admin_bp.route('/refunds')
@permission_required('manage_refunds')
def refunds():
    page = request.args.get('page', 1, type=int)
    items = Refund.query.order_by(desc(Refund.processed_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/refunds.html', refunds=items)


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
@admin_bp.route('/coupons')
@permission_required('manage_coupons')
def coupons():
    coupons = Coupon.query.order_by(desc(Coupon.created_at)).all()
    return render_template('admin/coupons.html', coupons=coupons)


@admin_bp.route('/coupons/new', methods=['GET', 'POST'])
@permission_required('manage_coupons')
def coupon_new():
    form = CouponForm()
    if form.validate_on_submit():
        coupon = Coupon(
            code=form.code.data.strip().upper(), description=form.description.data,
            discount_type=form.discount_type.data, discount_amount=form.discount_amount.data,
            start_date=form.start_date.data, expiry_date=form.expiry_date.data,
            usage_limit=form.usage_limit.data or 0, min_purchase=form.min_purchase.data or 0,
            max_discount=form.max_discount.data or 0, applies_to=form.applies_to.data,
            applies_to_id=form.applies_to_id.data or None, is_active=form.is_active.data)
        db.session.add(coupon)
        db.session.commit()
        log_action('create', 'coupon', coupon.id, f'Created coupon {coupon.code}')
        flash('Coupon created.', 'success')
        return redirect(url_for('admin.coupons'))
    return render_template('admin/coupon_form.html', form=form, coupon=None, title='New Coupon')


@admin_bp.route('/coupons/<int:coupon_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_coupons')
def coupon_edit(coupon_id):
    coupon = db.session.get(Coupon, coupon_id) or abort(404)
    form = CouponForm(obj=coupon)
    if form.validate_on_submit():
        coupon.code = form.code.data.strip().upper()
        coupon.description = form.description.data
        coupon.discount_type = form.discount_type.data
        coupon.discount_amount = form.discount_amount.data
        coupon.start_date = form.start_date.data
        coupon.expiry_date = form.expiry_date.data
        coupon.usage_limit = form.usage_limit.data or 0
        coupon.min_purchase = form.min_purchase.data or 0
        coupon.max_discount = form.max_discount.data or 0
        coupon.applies_to = form.applies_to.data
        coupon.applies_to_id = form.applies_to_id.data or None
        coupon.is_active = form.is_active.data
        db.session.commit()
        log_action('update', 'coupon', coupon.id, f'Updated coupon {coupon.code}')
        flash('Coupon updated.', 'success')
        return redirect(url_for('admin.coupons'))
    return render_template('admin/coupon_form.html', form=form, coupon=coupon, title='Edit Coupon')


@admin_bp.route('/coupons/<int:coupon_id>/delete', methods=['POST'])
@permission_required('manage_coupons')
def coupon_delete(coupon_id):
    coupon = db.session.get(Coupon, coupon_id) or abort(404)
    db.session.delete(coupon)
    db.session.commit()
    log_action('delete', 'coupon', coupon_id, f'Deleted coupon {coupon.code}')
    flash('Coupon deleted.', 'success')
    return redirect(url_for('admin.coupons'))


# ---------------------------------------------------------------------------
# Reviews moderation
# ---------------------------------------------------------------------------
@admin_bp.route('/reviews')
@permission_required('manage_reviews')
def reviews():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = Review.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(desc(Review.created_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/reviews.html', reviews=items, status=status)


@admin_bp.route('/reviews/<int:review_id>/approve', methods=['POST'])
@permission_required('manage_reviews')
def review_approve(review_id):
    r = db.session.get(Review, review_id) or abort(404)
    r.status = 'approved'
    db.session.commit()
    flash('Review approved.', 'success')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reviews/<int:review_id>/reject', methods=['POST'])
@permission_required('manage_reviews')
def review_reject(review_id):
    r = db.session.get(Review, review_id) or abort(404)
    r.status = 'rejected'
    db.session.commit()
    flash('Review rejected.', 'success')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@permission_required('manage_reviews')
def review_delete(review_id):
    r = db.session.get(Review, review_id) or abort(404)
    db.session.delete(r)
    db.session.commit()
    flash('Review deleted.', 'success')
    return redirect(url_for('admin.reviews'))


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
@admin_bp.route('/customers')
@permission_required('manage_customers')
def customers():
    page = request.args.get('page', 1, type=int)
    q = (request.args.get('q') or '').strip()
    query = User.query.filter_by(is_staff=False)
    if q:
        query = query.filter(User.full_name.ilike(f'%{q}%') | User.email.ilike(f'%{q}%'))
    items = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/customers.html', customers=items, q=q)


@admin_bp.route('/customers/<int:user_id>')
@permission_required('manage_customers')
def customer_detail(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.is_staff:
        abort(404)
    return render_template('admin/customer_detail.html', user=user)


@admin_bp.route('/customers/<int:user_id>/toggle', methods=['POST'])
@permission_required('manage_customers')
def customer_toggle(user_id):
    user = db.session.get(User, user_id) or abort(404)
    user.is_active = not user.is_active
    db.session.commit()
    log_action('update', 'customer', user.id, f'{"Blocked" if not user.is_active else "Unblocked"} customer {user.email}')
    flash('Customer status updated.', 'success')
    return redirect(url_for('admin.customers'))


@admin_bp.route('/customers/<int:user_id>/delete', methods=['POST'])
@permission_required('manage_customers')
def customer_delete(user_id):
    user = db.session.get(User, user_id) or abort(404)
    db.session.delete(user)
    db.session.commit()
    log_action('delete', 'customer', user_id, f'Deleted customer {user.email}')
    flash('Customer deleted.', 'success')
    return redirect(url_for('admin.customers'))


# ---------------------------------------------------------------------------
# Users & Roles
# ---------------------------------------------------------------------------
@admin_bp.route('/users')
@permission_required('manage_users')
def users():
    users = User.query.order_by(desc(User.created_at)).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@permission_required('manage_users')
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return render_template('admin/user_form.html', form=form, user=None, title='New User')
        user = User(full_name=form.full_name.data, email=form.email.data, phone=form.phone.data,
                    is_staff=form.is_staff.data, is_active=form.is_active.data)
        if form.password.data:
            user.set_password(form.password.data)
        else:
            user.set_password('changeme123')
        db.session.add(user)
        db.session.commit()
        log_action('create', 'user', user.id, f'Created user {user.email}')
        flash('User created.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, user=None, title='New User')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_users')
def user_edit(user_id):
    user = db.session.get(User, user_id) or abort(404)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        if User.query.filter(User.email == form.email.data, User.id != user.id).first():
            flash('Email already in use.', 'danger')
            return render_template('admin/user_form.html', form=form, user=user, title='Edit User')
        user.full_name = form.full_name.data
        user.email = form.email.data
        user.phone = form.phone.data
        user.is_staff = form.is_staff.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        log_action('update', 'user', user.id, f'Updated user {user.email}')
        flash('User updated.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, user=user, title='Edit User')


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@permission_required('manage_users')
def user_delete(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    log_action('delete', 'user', user_id, f'Deleted user {user.email}')
    flash('User deleted.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/roles')
@permission_required('manage_roles')
def roles():
    roles = Role.query.order_by(Role.name).all()
    return render_template('admin/roles.html', roles=roles, all_permissions=PERMISSIONS)


@admin_bp.route('/roles/new', methods=['GET', 'POST'])
@permission_required('manage_roles')
def role_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        perms = request.form.getlist('permissions')
        if not name:
            flash('Role name is required.', 'danger')
            return render_template('admin/role_form.html', role=None, all_permissions=PERMISSIONS)
        role = Role(name=name, description=description)
        db.session.add(role)
        db.session.flush()
        for p in perms:
            db.session.add(Permission(role_id=role.id, name=p))
        db.session.commit()
        log_action('create', 'role', role.id, f'Created role {role.name}')
        flash('Role created.', 'success')
        return redirect(url_for('admin.roles'))
    return render_template('admin/role_form.html', role=None, all_permissions=PERMISSIONS)


@admin_bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_roles')
def role_edit(role_id):
    role = db.session.get(Role, role_id) or abort(404)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        perms = request.form.getlist('permissions')
        if not name:
            flash('Role name is required.', 'danger')
            return render_template('admin/role_form.html', role=role, all_permissions=PERMISSIONS)
        role.name = name
        role.description = description
        Permission.query.filter_by(role_id=role.id).delete()
        for p in perms:
            db.session.add(Permission(role_id=role.id, name=p))
        db.session.commit()
        log_action('update', 'role', role.id, f'Updated role {role.name}')
        flash('Role updated.', 'success')
        return redirect(url_for('admin.roles'))
    current_perms = {p.name for p in role.permissions}
    return render_template('admin/role_form.html', role=role, all_permissions=PERMISSIONS, current_perms=current_perms)


@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@permission_required('manage_roles')
def role_delete(role_id):
    role = db.session.get(Role, role_id) or abort(404)
    if role.users.count():
        flash('Cannot delete role assigned to users.', 'danger')
        return redirect(url_for('admin.roles'))
    Permission.query.filter_by(role_id=role.id).delete()
    db.session.delete(role)
    db.session.commit()
    log_action('delete', 'role', role_id, f'Deleted role {role.name}')
    flash('Role deleted.', 'success')
    return redirect(url_for('admin.roles'))


# ---------------------------------------------------------------------------
# Content management
# ---------------------------------------------------------------------------
@admin_bp.route('/banners')
@permission_required('manage_content')
def banners():
    banners = Banner.query.order_by(Banner.position, Banner.display_order).all()
    return render_template('admin/banners.html', banners=banners)


@admin_bp.route('/banners/new', methods=['GET', 'POST'])
@permission_required('manage_content')
def banner_new():
    if request.method == 'POST':
        image = save_upload(request.files.get('image'), 'banners') if request.files.get('image') else None
        db.session.add(Banner(
            title=request.form.get('title'), subtitle=request.form.get('subtitle'),
            image=image, link=request.form.get('link'),
            position=request.form.get('position', 'home_hero'),
            active='active' in request.form,
            display_order=int(request.form.get('display_order', 0) or 0)))
        db.session.commit()
        flash('Banner created.', 'success')
        return redirect(url_for('admin.banners'))
    return render_template('admin/banner_form.html', banner=None)


@admin_bp.route('/banners/<int:banner_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_content')
def banner_edit(banner_id):
    banner = db.session.get(Banner, banner_id) or abort(404)
    if request.method == 'POST':
        if request.files.get('image'):
            if banner.image:
                delete_upload(banner.image)
            banner.image = save_upload(request.files.get('image'), 'banners')
        banner.title = request.form.get('title')
        banner.subtitle = request.form.get('subtitle')
        banner.link = request.form.get('link')
        banner.position = request.form.get('position', banner.position)
        banner.active = 'active' in request.form
        banner.display_order = int(request.form.get('display_order', 0) or 0)
        db.session.commit()
        flash('Banner updated.', 'success')
        return redirect(url_for('admin.banners'))
    return render_template('admin/banner_form.html', banner=banner)


@admin_bp.route('/banners/<int:banner_id>/delete', methods=['POST'])
@permission_required('manage_content')
def banner_delete(banner_id):
    banner = db.session.get(Banner, banner_id) or abort(404)
    if banner.image:
        delete_upload(banner.image)
    db.session.delete(banner)
    db.session.commit()
    flash('Banner deleted.', 'success')
    return redirect(url_for('admin.banners'))


@admin_bp.route('/pages')
@permission_required('manage_content')
def pages():
    pages = PageContent.query.order_by(PageContent.slug).all()
    return render_template('admin/pages.html', pages=pages)


@admin_bp.route('/pages/new', methods=['GET', 'POST'])
@permission_required('manage_content')
def page_new():
    if request.method == 'POST':
        slug = slugify(request.form.get('slug') or request.form.get('title'))
        if PageContent.query.filter_by(slug=slug).first():
            slug = unique_slug(PageContent, slug)
        db.session.add(PageContent(slug=slug, title=request.form.get('title'),
                                   content=request.form.get('content')))
        db.session.commit()
        flash('Page created.', 'success')
        return redirect(url_for('admin.pages'))
    return render_template('admin/page_form.html', page=None)


@admin_bp.route('/pages/<int:page_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_content')
def page_edit(page_id):
    page = db.session.get(PageContent, page_id) or abort(404)
    if request.method == 'POST':
        page.title = request.form.get('title')
        page.content = request.form.get('content')
        db.session.commit()
        flash('Page updated.', 'success')
        return redirect(url_for('admin.pages'))
    return render_template('admin/page_form.html', page=page)


@admin_bp.route('/pages/<int:page_id>/delete', methods=['POST'])
@permission_required('manage_content')
def page_delete(page_id):
    page = db.session.get(PageContent, page_id) or abort(404)
    db.session.delete(page)
    db.session.commit()
    flash('Page deleted.', 'success')
    return redirect(url_for('admin.pages'))


@admin_bp.route('/newsletter')
@permission_required('manage_content')
def newsletter():
    subs = NewsletterSubscriber.query.order_by(desc(NewsletterSubscriber.created_at)).all()
    return render_template('admin/newsletter.html', subscribers=subs)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@permission_required('manage_settings')
def settings():
    form = SettingsForm()
    if request.method == 'GET':
        from decimal import Decimal
        numeric_fields = {'tax_rate', 'shipping_flat', 'free_shipping_threshold'}
        for field in form:
            if field.name in ('csrf_token', 'submit'):
                continue
            val = Setting.query.filter_by(key=field.name).first()
            if val is not None and val.value is not None:
                if field.name in numeric_fields:
                    try:
                        field.data = Decimal(str(val.value))
                        continue
                    except Exception:
                        pass
                field.data = val.value
    if form.validate_on_submit():
        keys = ['store_name', 'store_currency', 'tax_rate', 'shipping_flat',
                'free_shipping_threshold', 'contact_email', 'contact_phone', 'address',
                'facebook', 'twitter', 'instagram']
        for key in keys:
            value = form.data.get(key)
            if value is None:
                continue
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                db.session.add(Setting(key=key, value=str(value)))
        db.session.commit()
        update_settings_cache(current_app)
        log_action('update', 'settings', None, 'Updated store settings')
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', form=form)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
@admin_bp.route('/notifications')
@permission_required('manage_notifications')
def notifications():
    page = request.args.get('page', 1, type=int)
    items = Notification.query.order_by(desc(Notification.created_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/notifications.html', notifications=items)


@admin_bp.route('/notifications/new', methods=['GET', 'POST'])
@permission_required('manage_notifications')
def notification_new():
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        ntype = request.form.get('type', 'system')
        target = request.form.get('target', 'all')
        link = request.form.get('link', '')
        if target == 'all':
            users = User.query.filter_by(is_active=True).all()
            for u in users:
                db.session.add(Notification(user_id=u.id, title=title, message=message, link=link, type=ntype))
        else:
            uid = request.form.get('user_id', type=int)
            if uid:
                db.session.add(Notification(user_id=uid, title=title, message=message, link=link, type=ntype))
        db.session.commit()
        flash('Notification sent.', 'success')
        return redirect(url_for('admin.notifications'))
    users = User.query.order_by(User.full_name).all()
    return render_template('admin/notification_form.html', users=users)


@admin_bp.route('/notifications/<int:notification_id>/delete', methods=['POST'])
@permission_required('manage_notifications')
def notification_delete(notification_id):
    n = db.session.get(Notification, notification_id) or abort(404)
    db.session.delete(n)
    db.session.commit()
    flash('Notification deleted.', 'success')
    return redirect(url_for('admin.notifications'))


# ---------------------------------------------------------------------------
# Support tickets
# ---------------------------------------------------------------------------
@admin_bp.route('/tickets')
@permission_required('manage_support')
def tickets():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = SupportTicket.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(desc(SupportTicket.created_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/tickets.html', tickets=items, status=status,
                           ticket_statuses=TICKET_STATUSES)


@admin_bp.route('/tickets/<int:ticket_id>', methods=['GET', 'POST'])
@permission_required('manage_support')
def ticket_detail(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id) or abort(404)
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if message:
            db.session.add(SupportReply(ticket_id=ticket.id, user_id=current_user.id,
                                        message=message, is_staff=True))
            ticket.status = 'replied'
            db.session.commit()
            flash('Reply sent.', 'success')
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket.id))
    return render_template('admin/ticket_detail.html', ticket=ticket, ticket_statuses=TICKET_STATUSES)


@admin_bp.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@permission_required('manage_support')
def ticket_update_status(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id) or abort(404)
    ticket.status = request.form.get('status', ticket.status)
    db.session.commit()
    flash('Ticket status updated.', 'success')
    return redirect(url_for('admin.ticket_detail', ticket_id=ticket.id))


# ---------------------------------------------------------------------------
# Activity logs
# ---------------------------------------------------------------------------
@admin_bp.route('/activity')
@permission_required('view_activity_logs')
def activity():
    page = request.args.get('page', 1, type=int)
    items = ActivityLog.query.order_by(desc(ActivityLog.created_at)).paginate(
        page=page, per_page=current_app.config['ADMIN_PER_PAGE'], error_out=False)
    return render_template('admin/activity.html', logs=items)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def _report_date_range():
    end = datetime.utcnow()
    start = end - timedelta(days=30)
    try:
        start = datetime.strptime(request.args.get('start', ''), '%Y-%m-%d')
    except ValueError:
        pass
    try:
        end = datetime.strptime(request.args.get('end', ''), '%Y-%m-%d')
    except ValueError:
        pass
    return start, end


@admin_bp.route('/reports/sales')
@permission_required('view_reports')
def report_sales():
    start, end = _report_date_range()
    end = end.replace(hour=23, minute=59, second=59)
    orders = Order.query.filter(Order.placed_at >= start, Order.placed_at <= end).order_by(Order.placed_at).all()
    total_revenue = sum(float(o.grand_total or 0) for o in orders if o.payment_status == 'paid')
    total_orders = len(orders)
    fmt = request.args.get('format', '')
    if fmt:
        rows = [['Order #', 'Date', 'Customer', 'Status', 'Payment', 'Total']]
        for o in orders:
            rows.append([o.order_number, o.placed_at.strftime('%Y-%m-%d %H:%M'),
                         o.customer.full_name if o.customer else '', o.status, o.payment_status, float(o.grand_total or 0)])
        rows.append([])
        rows.append(['TOTAL', '', '', '', '', total_revenue])
        if fmt == 'csv':
            return _csv_response(rows, 'sales_report.csv')
        if fmt == 'excel':
            return _excel_response(rows, 'sales_report.xlsx', 'Sales')
        if fmt == 'pdf':
            return _pdf_table_response('Sales Report', rows[0], rows[1:-2], 'sales_report.pdf')
    return render_template('admin/report_sales.html', orders=orders, total_revenue=total_revenue,
                           total_orders=total_orders, start=start, end=end)


@admin_bp.route('/reports/products')
@permission_required('view_reports')
def report_products():
    products = Product.query.order_by(desc(Product.sold_count)).limit(100).all()
    fmt = request.args.get('format', '')
    if fmt:
        rows = [['ID', 'Name', 'SKU', 'Price', 'Stock', 'Sold', 'Category']]
        for p in products:
            rows.append([p.id, p.name, p.sku, float(p.price or 0), p.stock_quantity or 0,
                         p.sold_count or 0, p.category.name if p.category else ''])
        if fmt == 'csv':
            return _csv_response(rows, 'product_report.csv')
        if fmt == 'excel':
            return _excel_response(rows, 'product_report.xlsx', 'Products')
        if fmt == 'pdf':
            return _pdf_table_response('Product Report', rows[0], rows[1:], 'product_report.pdf')
    return render_template('admin/report_products.html', products=products)


@admin_bp.route('/reports/customers')
@permission_required('view_reports')
def report_customers():
    customers = User.query.filter_by(is_staff=False).all()
    data = []
    for c in customers:
        orders = c.orders.all()
        spent = sum(float(o.grand_total or 0) for o in orders if o.payment_status == 'paid')
        data.append((c, len(orders), spent))
    data.sort(key=lambda x: x[2], reverse=True)
    fmt = request.args.get('format', '')
    if fmt:
        rows = [['ID', 'Name', 'Email', 'Orders', 'Total Spent']]
        for c, cnt, spent in data:
            rows.append([c.id, c.full_name, c.email, cnt, spent])
        if fmt == 'csv':
            return _csv_response(rows, 'customer_report.csv')
        if fmt == 'excel':
            return _excel_response(rows, 'customer_report.xlsx', 'Customers')
        if fmt == 'pdf':
            return _pdf_table_response('Customer Report', rows[0], rows[1:], 'customer_report.pdf')
    return render_template('admin/report_customers.html', customers=data)
