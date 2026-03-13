import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

PROJECT_ROOT = Path(__file__).resolve().parent / 'scriptura_api'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scriptura_api.settings')

application = get_wsgi_application()
