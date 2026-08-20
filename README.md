# ShopSphere — Online Shopping System

A complete, database-driven **Flask e-commerce application** with a customer storefront
and a full role-based admin management panel.

## Features

### Customer Storefront
- Product catalog with categories, subcategories, brands, search, filters & sorting
- Product detail pages with image gallery, variants, reviews, related products
- Shopping cart (guest + logged-in), wishlist, product comparison
- Multi-step checkout with multiple payment & shipping methods
- Order history, tracking, invoice (PDF), returns/refunds requests
- Customer account: profile, addresses, reviews, notifications
- Support tickets, FAQ, contact, newsletter, static content pages
- Coupons, flash sales, offers

### Admin Management Panel (`/admin`)
- **Dashboard** with stats and sales chart
- **Catalog**: products (CRUD, images, variants, specs), categories, brands
- **Sales**: orders, payments, deliveries, returns, refunds
- **Inventory**: stock levels, adjustments, movement history
- **Suppliers & Purchases**: supplier management, purchase recording
- **Customers**: customer list, detail, block/unblock
- **Staff**: users, roles & permissions (RBAC)
- **Marketing**: coupons, reviews moderation, banners, pages, newsletter
- **Support & System**: tickets, notifications, activity logs, settings
- **Reports**: sales / products / customers with CSV, Excel & PDF export

### Technical
- Flask application factory, SQLAlchemy ORM, PostgreSQL
- Flask-Login authentication, Werkzeug password hashing
- Role-Based Access Control (RBAC) with per-role permissions
- WTForms with CSRF protection
- ReportLab (PDF), openpyxl (Excel), csv exports
- Responsive UI with Bootstrap Icons, custom CSS
- Error pages (404/403/500/413)

## Requirements
- Python 3.10+
- PostgreSQL

## Installation

1. Clone the repository and create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   # source venv/bin/activate  # Linux/macOS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in `.env`:
   ```ini
   SECRET_KEY=your-secret-key
   DATABASE_URL=postgresql://user:password@localhost:5432/shopsphere
   MAIL_USERNAME=
   MAIL_PASSWORD=
   ```

4. Create the database and seed it:
   ```bash
   python seed.py
   ```
   This creates roles, an admin user, store settings, sample categories, brands and products.

5. Run the application:
   ```bash
   python run.py
   ```
   The app is available at `http://127.0.0.1:5000`.

## Default Admin Login
- **Email:** `admin@shopsphere.com`
- **Password:** `admin123`

> Change these credentials after first login.

## Project Structure
```
app/
  __init__.py            # Application factory, context processors, error handlers
  extensions.py          # db, login_manager, mail, migrate
  models/                # user, catalog, commerce, business, content
  routes/                # main, auth, products, cart, checkout, orders,
                         # reviews, support, admin
  services/              # cart_service, order_service
  forms/                 # customer_forms, admin_forms
  utils/                 # constants, helpers, decorators, activity, pdf
  templates/             # customer/, auth/, admin/, errors/
  static/                # css/, js/, img/
config.py
run.py
seed.py
requirements.txt
```

## Notes
- Tables are auto-created on first run (`db.create_all()` in the factory) for
  convenience; for production use Flask-Migrate migrations.
- Uploaded images are stored under `app/static/uploads/` (created automatically).
- The `ADMIN_PER_PAGE` config controls admin list pagination size.
"# os"  
