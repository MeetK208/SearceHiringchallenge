import os
import sys
import logging
from django.core.wsgi import get_wsgi_application

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

try:
    application = get_wsgi_application()
except Exception as e:
    logging.exception("WSGI application loading error: %s", str(e))
    raise
