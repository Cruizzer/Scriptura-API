from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model


class SettingsBasedSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Use credentials from settings.py instead of requiring database SocialApp."""
    
    def get_app(self, request, provider):
        """Override to get app from settings instead of database."""
        # Try to get from database first (if it exists)
        try:
            return super().get_app(request, provider)
        except Exception:
            # If not found in database, create a mock app object from settings
            from allauth.socialaccount.models import SocialApp
            from django.contrib.sites.models import Site
            
            providers = settings.SOCIALACCOUNT_PROVIDERS.get(provider, {})
            app_config = providers.get('APP', {})
            
            if not app_config.get('client_id'):
                raise ValueError(f"No {provider} credentials in settings")
            
            # Create or update persistent SocialApp object
            app, _ = SocialApp.objects.get_or_create(
                provider=provider,
                defaults={
                    'name': f"{provider.title()} OAuth",
                    'client_id': app_config.get('client_id'),
                    'secret': app_config.get('secret', ''),
                }
            )
            app.name = f"{provider.title()} OAuth"
            app.client_id = app_config.get('client_id')
            app.secret = app_config.get('secret', '')
            app.save()

            # Ensure current site is attached
            site = Site.objects.get_current()
            app.sites.add(site)
            
            return app

    def pre_social_login(self, request, sociallogin):
        """
        If a local user already exists with the same email, connect Google account
        to that user to avoid redirecting to /accounts/social/signup/.
        """
        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or '').strip()
        if not email:
            return

        User = get_user_model()
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            sociallogin.connect(request, existing_user)
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """Allow automatic signup to skip confirmation page."""
        return True
