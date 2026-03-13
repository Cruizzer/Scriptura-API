class PublicApiCacheHeadersMiddleware:
    """Attach cache headers to public, read-only API responses."""

    CACHED_PREFIXES = (
        '/api/books/',
        '/api/chapters/',
        '/api/verses/',
        '/api/book-summaries/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method == 'GET' and response.status_code == 200:
            if any(request.path.startswith(prefix) for prefix in self.CACHED_PREFIXES):
                # Shared cache (CDN): 5 min fresh, 10 min stale-while-revalidate.
                response['Cache-Control'] = 'public, s-maxage=300, stale-while-revalidate=600'

        return response
