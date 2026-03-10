# Scriptura-API
A RESTful API for analyzing the King James Bible. Provides hierarchical access to books, chapters, and verses, precomputed text analytics, and user-defined thematic insights.

## Architectural Highlights

* **Service layer** – analytics calculations live in `analytics/services` (e.g. `TextAnalyticsService`). Views delegate to services, demonstrating separation of concerns.
* **Repository pattern** – database access is abstracted in `core/repositories.py`; viewsets never touch ORM details directly.
* **DRF Best Practices** – uses `ViewSet`s, routers, filtering, search, and pagination. Custom filterset for verses allows `/api/verses/?book=Genesis&chapter=1&contains=light`.
* **Precomputation & Caching** – `BookSummary` model holds computed metrics (word count, entropy, TTR, hapax). Updated during ingestion to avoid repeated text processing.
* **Themes** – users can define themes with keywords and query coverage (`/api/themes/<id>/coverage/`).
* **Documentation** – OpenAPI schema available at `/api/schema/`, Swagger UI at `/api/docs/` thanks to DRF Spectacular.

## API Endpoints

| Route | Description |
|-------|-------------|
| `/api/books/` | list books (filter by testament, search by name) |
| `/api/chapters/` | list chapters (filter by book, number) |
| `/api/verses/` | list verses (filter by book, chapter, contains); search text |
| `/api/themes/` | CRUD themes and keywords |
| `/api/themes/<id>/coverage/` | analytics for theme across books |
| `/api/book-summaries/` | precomputed analytics per book |
| `/api/schema/` | OpenAPI JSON schema |
| `/api/docs/` | interactive Swagger documentation |

## Running the Project

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_usfm ../engDRA_usfm --reset
python manage.py load_pericopes ../engDRA_usfm/PericopeGroupedKJVVerses.json
``` 


