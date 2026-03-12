# Google OAuth Setup Instructions

This project now uses:

- Google Identity Services in the browser to get a Google `id_token`
- `POST /api/auth/google-token/` to exchange that Google token for this API's JWT tokens
- JWT bearer auth for protected API routes

It no longer uses the old `django-allauth` redirect flow.

## Step 1: Add credentials to `.env`

Set these values:

```dotenv
GOOGLE_CLIENT_ID=your_google_web_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

The frontend only needs `GOOGLE_CLIENT_ID`, but keeping the secret in `.env` is fine for future server-side Google integrations.

## Step 2: Use a **Web application** OAuth client in Google Cloud

In Google Cloud Console:

1. Go to https://console.cloud.google.com/
2. Open **APIs & Services** > **Credentials**
3. Create or edit an OAuth 2.0 Client ID
4. Make sure the client type is **Web application**

If you use a Desktop/Android/iOS client here, browser sign-in will fail.

## Step 3: Add **Authorized JavaScript origins**

Because this app now signs in directly from the browser, you must register the exact browser origin(s):

```text
http://127.0.0.1:8000
http://localhost:8000
```

If you access the site on a different port or hostname, add that exact origin too.

## Step 4: Redirect URIs are not the main setting anymore

For the current flow, the key setting is **Authorized JavaScript origins**, not the old allauth callback URLs.

You can leave redirect URIs empty unless you later add a server-side redirect-based Google OAuth flow.

## Step 5: Test the flow

1. Start the app with `python manage.py runserver`
2. Open `http://127.0.0.1:8000/`
3. Click **Sign in with Google**
4. Google returns an `id_token` to the frontend
5. The frontend sends it to `POST /api/auth/google-token/`
6. The API returns:
     - `access`
     - `refresh`
7. The frontend stores those JWTs and uses them on protected API requests

## Troubleshooting

- **"Access blocked: Authorization Error / no registered origin / invalid_client"**
    - Your Google Cloud OAuth client is missing the current browser origin.
    - Add both:
        - `http://127.0.0.1:8000`
        - `http://localhost:8000`
    - Then wait a minute and retry.

- **Button appears but sign-in fails immediately**
    - Confirm `GOOGLE_CLIENT_ID` in `.env` matches the exact Web OAuth client in Google Cloud.

- **Works on localhost but not 127.0.0.1**
    - Google treats these as different origins. Register both.

- **Still getting `invalid_client`**
    - Verify you are using a Web OAuth client, not another client type.

- **JWT requests fail after login**
    - Check that the frontend received tokens from `/api/auth/google-token/` and is sending `Authorization: Bearer <access>`.
