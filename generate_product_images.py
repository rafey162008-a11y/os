"""Generate distinct offline SVG images for the sample products.

No internet required. Each product gets a unique color and a simple line-art
icon plus its name. Output goes to app/static/img/products/.

Usage:
    python generate_product_images.py
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, 'app', 'static', 'img', 'products')

# Each entry: filename, display label, gradient colors (top, bottom), icon svg markup
PRODUCTS = [
    (
        'smartphone-x.svg', 'Smartphone X', '#0ea5e9', '#2563eb',
        '''
        <rect x="235" y="150" width="130" height="300" rx="22" fill="#ffffff" opacity="0.95"/>
        <rect x="248" y="178" width="104" height="220" rx="8" fill="#0ea5e9" opacity="0.85"/>
        <circle cx="300" cy="420" r="10" fill="#0ea5e9" opacity="0.85"/>
        <rect x="288" y="162" width="24" height="6" rx="3" fill="#0ea5e9" opacity="0.85"/>
        '''
    ),
    (
        'laptop-pro-15.svg', 'Laptop Pro 15', '#6366f1', '#4338ca',
        '''
        <rect x="180" y="200" width="240" height="150" rx="12" fill="#ffffff" opacity="0.95"/>
        <rect x="196" y="216" width="208" height="118" rx="6" fill="#6366f1" opacity="0.85"/>
        <path d="M150 350 h300 l24 40 h-348 z" fill="#ffffff" opacity="0.95"/>
        <rect x="270" y="362" width="60" height="8" rx="4" fill="#6366f1" opacity="0.85"/>
        '''
    ),
    (
        'wireless-earbuds.svg', 'Wireless Earbuds', '#f59e0b', '#d97706',
        '''
        <circle cx="255" cy="280" r="42" fill="#ffffff" opacity="0.95"/>
        <rect x="248" y="300" width="14" height="70" rx="7" fill="#ffffff" opacity="0.95"/>
        <circle cx="345" cy="280" r="42" fill="#ffffff" opacity="0.95"/>
        <rect x="338" y="300" width="14" height="70" rx="7" fill="#ffffff" opacity="0.95"/>
        <circle cx="255" cy="280" r="18" fill="#f59e0b" opacity="0.85"/>
        <circle cx="345" cy="280" r="18" fill="#f59e0b" opacity="0.85"/>
        '''
    ),
    (
        'men-t-shirt.svg', 'Men T-Shirt', '#10b981', '#059669',
        '''
        <path d="M240 200 l60 30 l60 -30 l50 40 l-30 50 l-30 -20 l0 150 l-100 0 l0 -150 l-30 20 l-30 -50 z"
              fill="#ffffff" opacity="0.95"/>
        <path d="M300 230 q-30 0 -30 30 q30 -10 60 0 q0 -30 -30 -30 z" fill="#10b981" opacity="0.85"/>
        '''
    ),
    (
        'running-shoes.svg', 'Running Shoes', '#ef4444', '#dc2626',
        '''
        <path d="M200 360 q0 -40 60 -50 l40 -40 q30 -20 60 -10 l40 20 q40 10 40 50 l0 30 l-240 0 z"
              fill="#ffffff" opacity="0.95"/>
        <path d="M200 360 l240 0 l0 20 l-240 0 z" fill="#ef4444" opacity="0.85"/>
        <path d="M260 320 l20 -20 M300 310 l20 -20 M340 305 l20 -15" stroke="#ef4444" stroke-width="6" stroke-linecap="round"/>
        '''
    ),
    (
        'office-chair.svg', 'Office Chair', '#8b5cf6', '#7c3aed',
        '''
        <rect x="250" y="170" width="100" height="110" rx="20" fill="#ffffff" opacity="0.95"/>
        <rect x="262" y="290" width="76" height="40" rx="14" fill="#ffffff" opacity="0.95"/>
        <rect x="290" y="330" width="20" height="90" fill="#ffffff" opacity="0.95"/>
        <path d="M250 420 h100 l-10 30 h-80 z" fill="#ffffff" opacity="0.95"/>
        <circle cx="270" cy="445" r="10" fill="#8b5cf6" opacity="0.85"/>
        <circle cx="330" cy="445" r="10" fill="#8b5cf6" opacity="0.85"/>
        '''
    ),
    (
        'cookware-set.svg', 'Cookware Set', '#14b8a6', '#0d9488',
        '''
        <path d="M220 280 h160 v60 q0 50 -80 50 q-80 0 -80 -50 z" fill="#ffffff" opacity="0.95"/>
        <rect x="210" y="270" width="180" height="18" rx="9" fill="#ffffff" opacity="0.95"/>
        <path d="M380 280 q40 0 40 30 q0 30 -40 30" fill="none" stroke="#ffffff" stroke-width="12" opacity="0.95"/>
        <circle cx="300" cy="250" r="14" fill="#14b8a6" opacity="0.85"/>
        '''
    ),
    (
        'fitness-tracker.svg', 'Fitness Tracker', '#ec4899', '#db2777',
        '''
        <rect x="270" y="180" width="60" height="240" rx="20" fill="#ffffff" opacity="0.95"/>
        <rect x="282" y="220" width="36" height="160" rx="10" fill="#ec4899" opacity="0.85"/>
        <circle cx="300" cy="300" r="22" fill="#ffffff" opacity="0.95"/>
        <path d="M300 288 v24 M288 300 h24" stroke="#ec4899" stroke-width="5" stroke-linecap="round"/>
        '''
    ),
]


def build_svg(label, c1, c2, icon):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600" role="img" aria-label="{label}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="600" height="600" fill="url(#g)"/>
  <circle cx="300" cy="300" r="250" fill="#ffffff" opacity="0.08"/>
  {icon}
  <text x="300" y="520" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="34" font-weight="700" fill="#ffffff">{label}</text>
</svg>
'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for fname, label, c1, c2, icon in PRODUCTS:
        path = os.path.join(OUT_DIR, fname)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(build_svg(label, c1, c2, icon))
        print(f"Wrote {path}")
    print(f"\nGenerated {len(PRODUCTS)} product images in {OUT_DIR}")


if __name__ == '__main__':
    main()
