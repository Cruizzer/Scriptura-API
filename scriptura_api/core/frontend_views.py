from django.views.generic import TemplateView
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings


class FrontendView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['google_client_id'] = settings.GOOGLE_CLIENT_ID
        return context


class GoogleSigninView(TemplateView):
    template_name = 'socialaccount/login.html'


@require_http_methods(["GET"])
def auth_status_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "is_authenticated": False,
            "name": "",
            "email": "",
            "avatar_url": "",
        })

    return JsonResponse({
        "is_authenticated": True,
        "name": request.user.get_full_name() or request.user.get_username() or "",
        "email": request.user.email or "",
        "avatar_url": "",
        "id": request.user.id,
    })
