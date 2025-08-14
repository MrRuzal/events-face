import os
import sys

from django.core.asgi import get_asgi_application

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.dirname(BASE_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_asgi_application()
