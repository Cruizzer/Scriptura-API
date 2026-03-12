# Scriptura API

A RESTful API for analyzing the Douay-Rheims 1899 American Edition (DRA) translation. Provides hierarchical access to books, chapters, and verses with advanced text analytics, thematic analysis, and lexical similarity computations.

## Overview

Scriptura API is a Django REST Framework application designed to serve biblical text data with sophisticated analytics capabilities. The system supports:

- Full biblical text access (books, chapters, verses)
- Precomputed text metrics (word count, entropy, lexical diversity)
- User-defined thematic collections with keyword matching
- Curated verse collections with multiple-relationship management
- Advanced NLP-based lexical similarity analysis and verse recommendations

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Virtual environment support

### Installation Steps

1. **Clone the repository and navigate to the project:**

```bash
git clone <your-repo-url>
cd Scriptura-API
```

2. **Create and activate a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Apply database migrations:**

```bash
cd scriptura_api
python manage.py migrate
```

5. **Load biblical text data:**

```bash
# Optional: regenerate scraped notes JSON from pg8300 source text
python manage.py scrape_douay_notes --input ../pg8300.txt --output ../douay_notes_scraped.json

python manage.py load_usfm ../engDRA_usfm --reset
python manage.py load_pericopes ../engDRA_usfm/PericopeGroupedKJVVerses.json
python manage.py load_douay_notes ../douay_notes_scraped.json
```

6. **Start the development server:**

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/`

## Architecture

The project follows Django REST Framework best practices with clear separation of concerns:

- **Service Layer**: Analytics calculations in `analytics/services/` (e.g., `TextAnalyticsService`, `SimilarityAnalyticsService`)
- **Repository Pattern**: Database access abstracted in `core/repositories.py`
- **ViewSets**: DRF `ViewSet` implementations for standardized API operations
- **Serializers**: Separate read and write serializers for optimization
- **Precomputation**: `BookSummary` model holds computed metrics to avoid redundant processing

## API Documentation

### Interactive Documentation

Access the interactive API documentation at:
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

### Core Endpoints

#### Biblical Text Access
- `GET /api/books/` - List books (filter by testament, search by name)
- `GET /api/chapters/` - List chapters (filter by book, number)
- `GET /api/verses/` - List verses (filter by book/chapter/keywords; full-text search)

#### Themes
- `GET /api/themes/` - List themes
- `POST /api/themes/` - Create theme with keywords
- `GET /api/themes/{id}/coverage/` - Analytics for theme across books

#### Collections
- `GET /api/collections/` - List verse collections
- `POST /api/collections/` - Create collection (many-to-many verses and themes)
- `PUT /api/collections/{id}/` - Update collection
- `DELETE /api/collections/{id}/` - Delete collection

#### Analytics
- `GET /api/book-summaries/` - Precomputed metrics per book
- `GET /api/analytics/similarity-graph/` - Book similarity network (configurable metric and threshold)
- `GET /api/analytics/verse-recommendations/` - Find similar verses to a reference verse

## Key Features

### Collections CRUD System
User-created collections link verses and themes for organized biblical study. Includes:
- Full Create-Read-Update-Delete operations
- Many-to-many relationships with verses and themes
- Full-text search on name and description
- Automatic timestamp tracking

### Lexical Similarity Analytics
Advanced NLP analytics computing vocabulary and thematic relationships:
- Multiple similarity metrics (cosine, Jaccard)
- Configurable threshold filtering
- Graph format for visualization (nodes and edges)
- Smart verse recommendation engine
- Efficient vector-based text analysis

## Testing

Run the test suite with:

```bash
python manage.py test
```

All tests pass with no errors or warnings.

## Example Usage

### Create a Collection

```bash
curl -X POST http://localhost:8000/api/collections/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hope and Redemption",
    "description": "Key passages on redemption",
    "verses": [1, 2, 3],
    "themes": [1, 2]
  }'
```

### Get Book Similarity Graph

```bash
curl "http://localhost:8000/api/analytics/similarity-graph/?threshold=0.5&metric=cosine"
```

### Find Similar Verses

```bash
curl "http://localhost:8000/api/analytics/verse-recommendations/?verse_id=100&top_k=5"
```

## Project Structure

```
scriptura_api/
  core/              # Core models, serializers, views
  analytics/         # Text analytics and similarity computations
  ingestion/         # Data loading and processing
  templates/         # Frontend templates
  manage.py          # Django management script
  db.sqlite3         # Database
```

## Version Control

This project uses Git for version control. The repository includes a complete commit history demonstrating development progress. Clone or view the repository to see all changes.

## License

Refer to the LICENSE file for licensing information. 


