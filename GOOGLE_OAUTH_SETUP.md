# Google OAuth Setup Instructions

## Step 1: Add Your Credentials

Edit `scriptura_api/scriptura_api/settings.py` and add your Google OAuth credentials:

```python
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': 'YOUR_CLIENT_ID_HERE',
            'secret': 'YOUR_CLIENT_SECRET_HERE',
            'key': ''
        }
    }
}
```

## Step 2: Configure Google Cloud Console

1. Go to https://console.cloud.google.com/
2. Select your project (or create a new one)
3. Navigate to **APIs & Services** > **Credentials**
4. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:8000/accounts/google/login/callback/
   http://127.0.0.1:8000/accounts/google/login/callback/
   ```

## Step 3: Add Social App in Django Admin

1. Run the server: `python manage.py runserver`
2. Go to http://localhost:8000/admin/
3. Create a superuser if you haven't: `python manage.py createsuperuser`
4. Log in to admin
5. Go to **Sites** and make sure you have a site (should be `example.com` by default, ID=1)
6. Go to **Social applications** > **Add social application**
   - Provider: Google
   - Name: Google OAuth
   - Client ID: (paste your Client ID)
   - Secret key: (paste your Secret)
   - Sites: Select "example.com" (or your site)
   - Save

## Step 4: Test

1. Go to http://localhost:8000/
2. Click "Sign in with Google"
3. You should be redirected to Google's OAuth consent screen
4. After authorization, you'll be redirected back to your app

## Step 5: Update Collection Model (Optional)

To tie collections to specific users, you'll need to add a user ForeignKey to the Collection model and run migrations.

## Troubleshooting

- **"Redirect URI mismatch"**: Make sure the redirect URI in Google Cloud Console matches exactly
- **"Site matching query does not exist"**: Make sure SITE_ID=1 in settings and you have a Site with ID=1 in Django admin
- **CSRF errors**: Make sure you're accessing via the same domain (don't mix localhost and 127.0.0.1)
