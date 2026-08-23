"""WSGI entry point for PythonAnywhere (and other WSGI servers).

On PythonAnywhere, copy the contents of this file into your web app's
WSGI configuration file (e.g. /var/www/youruser_yourdomain_com_wsgi.py),
adjust the paths below, and then click "Reload" on the Web tab.

Key points:
- The project directory must be on sys.path.
- If you use a virtualenv, activate it (see commented block).
- The WSGI server expects a callable named `application`.
"""
import sys
import os

# Directory that contains this file (the project root).
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# --- Optional: activate a virtualenv (uncomment and edit the path) ---
# venv_path = '/home/yourusername/.virtualenvs/yourenv'
# activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')
# if os.path.exists(activate_this):
#     with open(activate_this) as f:
#         exec(f.read(), {'__file__': activate_this})

# Load environment variables from .env if present (PythonAnywhere does not
# automatically read .env, so set vars in the WSGI file or the dashboard).
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

from app import create_app

application = create_app()

if __name__ == '__main__':
    application.run()
