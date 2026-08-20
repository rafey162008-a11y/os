"""WTForms definitions for customer, auth and admin forms."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, BooleanField, TextAreaField,
                     SelectField, IntegerField, DecimalField, DateField,
                     SubmitField, FloatField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Optional,
                                NumberRange, ValidationError, Regexp)

from app.models.user import User
from app.models.catalog import Product


# ============================================================
# Auth forms
# ============================================================
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember me')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=30)])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(min=6, max=128),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d).+$', message='Password must contain letters and numbers.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    accept_terms = BooleanField('I agree to the Terms & Conditions', validators=[DataRequired()])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError('An account with this email already exists.')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(min=6, max=128),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d).+$', message='Password must contain letters and numbers.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Reset Password')


# ============================================================
# Customer forms
# ============================================================
class AddressForm(FlaskForm):
    label = StringField('Label', validators=[Optional(), Length(max=60)],
                        default='Home')
    country = StringField('Country', default='Pakistan')
    province = StringField('Province/State', validators=[Optional(), Length(max=80)])
    city = StringField('City', validators=[DataRequired(), Length(max=80)])
    area = StringField('Area', validators=[Optional(), Length(max=120)])
    street_address = StringField('Street Address', validators=[DataRequired(), Length(max=255)])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=20)])
    phone = StringField('Phone', validators=[Optional(), Length(max=30)])
    is_default = BooleanField('Set as default address')
    submit = SubmitField('Save Address')


class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=120)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=30)])
    avatar = FileField('Profile Picture', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only')])
    submit = SubmitField('Update Profile')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(), Length(min=6, max=128),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d).+$', message='Password must contain letters and numbers.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Change Password')


# ============================================================
# Checkout / support forms
# ============================================================
class CheckoutForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=30)])
    country = StringField('Country', default='Pakistan')
    province = StringField('Province/State', validators=[Optional(), Length(max=80)])
    city = StringField('City', validators=[DataRequired(), Length(max=80)])
    area = StringField('Area', validators=[Optional(), Length(max=120)])
    street_address = StringField('Street Address', validators=[DataRequired(), Length(max=255)])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=20)])
    shipping_method = SelectField('Shipping Method', choices=[
        ('standard', 'Standard Delivery'), ('express', 'Express Delivery'),
        ('pickup', 'Store Pickup')
    ], default='standard')
    payment_method = SelectField('Payment Method', choices=[
        ('cod', 'Cash on Delivery'), ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'), ('wallet', 'Digital Wallet'),
        ('online', 'Online Payment Gateway'), ('mobile', 'Mobile Payment')
    ], default='cod')
    coupon_code = StringField('Coupon Code', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('Order Notes', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Place Order')


class CouponApplyForm(FlaskForm):
    code = StringField('Coupon Code', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('Apply Coupon')


class ReviewForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])
    title = StringField('Title', validators=[Optional(), Length(max=150)])
    comment = TextAreaField('Review', validators=[DataRequired(), Length(min=10, max=2000)])
    image = FileField('Product Image', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only')])
    submit = SubmitField('Submit Review')


class ReturnForm(FlaskForm):
    reason = SelectField('Return Reason', choices=[
        ('damaged', 'Damaged or defective'), ('wrong_item', 'Wrong item received'),
        ('not_as_described', 'Not as described'), ('size_issue', 'Size/color issue'),
        ('changed_mind', 'Changed my mind'), ('other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    evidence = FileField('Evidence Images', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only')])
    submit = SubmitField('Submit Return Request')


class SupportTicketForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', choices=[
        ('general', 'General'), ('order', 'Order'), ('payment', 'Payment'),
        ('delivery', 'Delivery'), ('return', 'Return'), ('complaint', 'Complaint')
    ], default='general')
    priority = SelectField('Priority', choices=[
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')
    ], default='normal')
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=4000)])
    submit = SubmitField('Submit Ticket')


class TicketReplyForm(FlaskForm):
    message = TextAreaField('Reply', validators=[DataRequired(), Length(min=1, max=4000)])
    submit = SubmitField('Send Reply')


class NewsletterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Subscribe')
