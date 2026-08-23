"""WSGI entry point for PythonAnywhere (and other WSGI servers).

On PythonAnywhere, copy the contents of this file into your web app's
WSGI configuration file (e.g. /var/www/youruser_yourdomain_com_wsgi.py),
adjust the paths below, and then click "Reload" on the Web tab.

Key points:
- The project directory must be on sys.path.
- If you use a virtualenv, activate it (see commented block).
- The WSGI server expects a callable named `application`.
- Startup errors are caught and logged to stderr so they appear in the
  PythonAnywhere Error log instead of a generic "Something went wrong" page.
"""
import sys
import os
import traceback

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
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_home, '.env'))
except Exception as e:  # pragma: no cover - defensive
    sys.stderr.write(f"[wsgi] Could not load .env: {e}\n")

application = None
try:
    from app import create_app
    application = create_app()
except Exception:
    # Log the full traceback to the server error log so the real cause is
    # visible (PythonAnywhere shows a generic page otherwise).
    sys.stderr.write("=" * 70 + "\n")
    sys.stderr.write("FATAL: application failed to start in wsgi.py\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.write("=" * 70 + "\n")
    raise

if __name__ == '__main__':
    application.run()
