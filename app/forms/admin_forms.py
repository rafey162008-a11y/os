"""WTForms for the admin panel."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, TextAreaField, SelectField, IntegerField,
                     DecimalField, BooleanField, SubmitField, DateField, FloatField)
from wtforms.validators import (DataRequired, Optional, Length, NumberRange, Email)


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    parent_id = SelectField('Parent Category', coerce=int, choices=[(0, 'None (Top Level)')])
    image = FileField('Category Image', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only')])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    display_order = IntegerField('Display Order', default=0, validators=[Optional()])
    submit = SubmitField('Save Category')


class BrandForm(FlaskForm):
    name = StringField('Brand Name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    logo = FileField('Brand Logo', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'], 'Images only')])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    submit = SubmitField('Save Brand')


class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=255)])
    sku = StringField('SKU / Product Code', validators=[Optional(), Length(max=80)])
    category_id = SelectField('Category', coerce=int, choices=[(0, 'Select Category')], validators=[DataRequired()])
    subcategory_id = SelectField('Subcategory', coerce=int, choices=[(0, 'None')], validators=[Optional()])
    brand_id = SelectField('Brand', coerce=int, choices=[(0, 'Select Brand')], validators=[Optional()])
    price = DecimalField('Price', validators=[DataRequired(), NumberRange(min=0)])
    old_price = DecimalField('Old Price', validators=[Optional(), NumberRange(min=0)])
    cost_price = DecimalField('Cost Price', validators=[Optional(), NumberRange(min=0)])
    stock_quantity = IntegerField('Stock Quantity', default=0, validators=[Optional(), NumberRange(min=0)])
    min_stock_level = IntegerField('Minimum Stock Level', default=5, validators=[Optional(), NumberRange(min=0)])
    short_description = TextAreaField('Short Description', validators=[Optional(), Length(max=500)])
    description = TextAreaField('Full Description', validators=[Optional()])
    colors = StringField('Colors (comma separated)', validators=[Optional(), Length(max=255)])
    sizes = StringField('Sizes (comma separated)', validators=[Optional(), Length(max=255)])
    main_image = FileField('Main Image', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only')])
    video_url = StringField('Product Video URL', validators=[Optional(), Length(max=255)])
    warranty_info = TextAreaField('Warranty Information', validators=[Optional()])
    return_policy = TextAreaField('Return Policy', validators=[Optional()])
    shipping_info = TextAreaField('Shipping Information', validators=[Optional()])
    condition = SelectField('Condition', choices=[
        ('new', 'New'), ('used', 'Used'), ('refurbished', 'Refurbished')
    ], default='new')
    is_featured = BooleanField('Featured')
    is_bestseller = BooleanField('Best Seller')
    is_new_arrival = BooleanField('New Arrival')
    is_flash_sale = BooleanField('Flash Sale')
    is_recommended = BooleanField('Recommended')
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    submit = SubmitField('Save Product')


class VariantForm(FlaskForm):
    name = StringField('Variant Name', validators=[DataRequired(), Length(max=120)])
    sku = StringField('Variant SKU', validators=[Optional(), Length(max=100)])
    price = DecimalField('Variant Price', validators=[Optional(), NumberRange(min=0)])
    stock_quantity = IntegerField('Variant Stock', default=0, validators=[Optional(), NumberRange(min=0)])
    attributes = StringField('Attributes (JSON)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Variant')


class SpecificationForm(FlaskForm):
    label = StringField('Label', validators=[DataRequired(), Length(max=120)])
    value = StringField('Value', validators=[DataRequired(), Length(max=255)])
    submit = SubmitField('Add Specification')


class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired(), Length(max=150)])
    company = StringField('Company', validators=[Optional(), Length(max=150)])
    phone = StringField('Phone', validators=[Optional(), Length(max=30)])
    email = StringField('Email', validators=[Optional(), Email()])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    status = SelectField('Status', choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    submit = SubmitField('Save Supplier')


class PurchaseForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, choices=[], validators=[DataRequired()])
    reference = StringField('Reference', validators=[Optional(), Length(max=100)])
    product_id = SelectField('Product', coerce=int, choices=[], validators=[DataRequired()])
    quantity = IntegerField('Quantity', default=1, validators=[DataRequired(), NumberRange(min=1)])
    unit_cost = DecimalField('Unit Cost', validators=[DataRequired(), NumberRange(min=0)])
    amount_paid = DecimalField('Amount Paid', validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Purchase')


class CouponForm(FlaskForm):
    code = StringField('Coupon Code', validators=[DataRequired(), Length(min=3, max=50)])
    description = StringField('Description', validators=[Optional(), Length(max=255)])
    discount_type = SelectField('Discount Type', choices=[
        ('percentage', 'Percentage (%)'), ('fixed', 'Fixed Amount')
    ], default='percentage')
    discount_amount = DecimalField('Discount Amount', validators=[DataRequired(), NumberRange(min=0)])
    start_date = DateField('Start Date', validators=[Optional()])
    expiry_date = DateField('Expiry Date', validators=[Optional()])
    usage_limit = IntegerField('Usage Limit (0 = unlimited)', default=0, validators=[Optional(), NumberRange(min=0)])
    min_purchase = DecimalField('Minimum Purchase', default=0, validators=[Optional(), NumberRange(min=0)])
    max_discount = DecimalField('Maximum Discount (0 = none)', default=0, validators=[Optional(), NumberRange(min=0)])
    applies_to = SelectField('Applies To', choices=[
        ('all', 'All Products'), ('product', 'Specific Product'),
        ('category', 'Specific Category'), ('brand', 'Specific Brand')
    ], default='all')
    applies_to_id = IntegerField('Target ID (Product/Category/Brand)', default=0, validators=[Optional(), NumberRange(min=0)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Coupon')


class UserForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=30)])
    password = StringField('Password (leave blank to keep)', validators=[Optional(), Length(min=6, max=128)])
    is_staff = BooleanField('Staff Account')
    is_active = BooleanField('Active')
    submit = SubmitField('Save User')


class SettingsForm(FlaskForm):
    store_name = StringField('Store Name', validators=[Optional(), Length(max=120)])
    store_currency = StringField('Currency Symbol', validators=[Optional(), Length(max=10)])
    tax_rate = DecimalField('Tax Rate (%)', default=0, validators=[Optional(), NumberRange(min=0, max=100)])
    shipping_flat = DecimalField('Flat Shipping Charge', default=5, validators=[Optional(), NumberRange(min=0)])
    free_shipping_threshold = DecimalField('Free Shipping Above', default=100, validators=[Optional(), NumberRange(min=0)])
    contact_email = StringField('Contact Email', validators=[Optional(), Email()])
    contact_phone = StringField('Contact Phone', validators=[Optional(), Length(max=30)])
    address = TextAreaField('Store Address', validators=[Optional()])
    facebook = StringField('Facebook URL', validators=[Optional(), Length(max=255)])
    twitter = StringField('Twitter URL', validators=[Optional(), Length(max=255)])
    instagram = StringField('Instagram URL', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Settings')
