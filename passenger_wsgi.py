import os
import sys

# Get the directory containing this file (project root)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Import Django WSGI handler
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
