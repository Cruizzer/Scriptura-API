from django.views.generic import TemplateView
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse


class FrontendView(TemplateView):
    template_name = 'index.html'


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

    avatar_url = ""
    try:
        from allauth.socialaccount.models import SocialAccount

        sa = (
            SocialAccount.objects
            .filter(user=request.user, provider='google')
            .first()
        )
        if sa:
            avatar_url = (
                sa.extra_data.get('picture')
                or sa.extra_data.get('avatar_url')
                or ""
            )
    except Exception:
        avatar_url = ""

    return JsonResponse({
        "is_authenticated": True,
        "name": request.user.get_full_name() or request.user.get_username() or "",
        "email": request.user.email or "",
        "avatar_url": avatar_url,
        "id": request.user.id,
    })
