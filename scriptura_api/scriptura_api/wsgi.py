"""
WSGI config for scriptura_api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# Ensure imports work whether deployment root is repository root
# or the inner "scriptura_api" directory.
CURRENT_DIR = Path(__file__).resolve().parent
INNER_PROJECT_ROOT = CURRENT_DIR.parent
REPO_ROOT = INNER_PROJECT_ROOT.parent

for candidate in (str(INNER_PROJECT_ROOT), str(REPO_ROOT)):
	if candidate not in sys.path:
		sys.path.insert(0, candidate)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scriptura_api.settings')

# Fallback for environments where package resolution is nested from repo root.
if os.environ.get('DJANGO_SETTINGS_MODULE') == 'scriptura_api.settings':
	try:
		__import__('scriptura_api.settings')
	except ModuleNotFoundError:
		os.environ['DJANGO_SETTINGS_MODULE'] = 'scriptura_api.scriptura_api.settings'

application = get_wsgi_application()
