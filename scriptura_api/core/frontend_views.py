from django.views.generic import TemplateView
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse


class FrontendView(TemplateView):
    template_name = 'index.html'
