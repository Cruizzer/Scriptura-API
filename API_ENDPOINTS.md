# API Endpoints Reference

## Existing Endpoints (Read-Only)

### Books
```
GET    /api/books/                     List all books
GET    /api/books/{id}/                Get a specific book
GET    /api/books/?testament=OT        Filter by testament
GET    /api/books/?search=Genesis      Search by name
```

### Chapters
```
GET    /api/chapters/                  List all chapters
GET    /api/chapters/{id}/             Get a specific chapter
GET    /api/chapters/?book_name=Genesis&number=1  Filter by book and number
```

### Verses
```
GET    /api/verses/                    List all verses
GET    /api/verses/{id}/               Get a specific verse
GET    /api/verses/?book=Genesis&chapter=1&contains=light  Advanced filtering
GET    /api/verses/?search=faith       Search verse text
```

### Themes (Existing)
```
GET    /api/themes/                    List all themes
GET    /api/themes/{id}/               Get a specific theme
GET    /api/themes/{id}/coverage/      Get theme coverage across books
POST   /api/themes/                    Create a theme
PUT    /api/themes/{id}/               Update a theme
DELETE /api/themes/{id}/               Delete a theme
```

### Theme Keywords (Existing)
```
GET    /api/theme-keywords/            List all keywords
POST   /api/theme-keywords/            Create a keyword
PUT    /api/theme-keywords/{id}/       Update a keyword
DELETE /api/theme-keywords/{id}/       Delete a keyword
```

### Book Summaries
```
GET    /api/book-summaries/            List precomputed analytics
GET    /api/book-summaries/{id}/       Get analytics for a book
```

---

## NEW ENDPOINTS (Features Added)

### Collections - Full CRUD ⭐
```
GET    /api/collections/               List all collections
GET    /api/collections/{id}/          Get a specific collection
GET    /api/collections/?search=hope   Search collections
POST   /api/collections/               CREATE a new collection
PUT    /api/collections/{id}/          UPDATE a collection
PATCH  /api/collections/{id}/          Partial update
DELETE /api/collections/{id}/          DELETE a collection
```

**Collection Request Body:**
```json
{
  "name": "Hope in Crisis",
  "description": "Verses about trusting God during hardship",
  "verses": [123, 456, 789],
  "themes": [1, 2]
}
```

**Collection Response:**
```json
{
  "id": 1,
  "name": "Hope in Crisis",
  "description": "Verses about trusting God during hardship",
  "verses": [
    {
      "id": 123,
      "number": 16,
      "text": "For God so loved the world...",
      "book_name": "John",
      "chapter_number": 3,
      ...
    }
  ],
  "themes": ["Redemption", "Love"],
  "verse_count": 3,
  "theme_count": 2,
  "created_at": "2025-03-04T10:30:00Z",
  "updated_at": "2025-03-04T11:45:00Z"
}
```

---

### Lexical Similarity Graph ⭐⭐

#### Get Book Similarity Network
```
GET /api/analytics/similarity-graph/
GET /api/analytics/similarity-graph/?threshold=0.3
GET /api/analytics/similarity-graph/?metric=cosine
GET /api/analytics/similarity-graph/?metric=jaccard&threshold=0.5
```

**Parameters:**
- `metric` (optional): "cosine" (default) or "jaccard"
- `threshold` (optional): Minimum similarity (0.0-1.0, default 0.3)

**Response:**
```json
{
  "nodes": [
    {
      "id": "Genesis",
      "book_id": 1,
      "testament": "OT",
      "size": 50
    },
    {
      "id": "Exodus",
      "book_id": 2,
      "testament": "OT",
      "size": 40
    },
    {
      "id": "Matthew",
      "book_id": 40,
      "testament": "NT",
      "size": 28
    }
  ],
  "edges": [
    {
      "source": "Genesis",
      "target": "Exodus",
      "weight": 0.78
    },
    {
      "source": "Genesis",
      "target": "Revelation",
      "weight": 0.65
    }
  ],
  "metric": "cosine",
  "threshold": 0.3
}
```

**Use Cases:**
- Feed into D3.js for force-directed graph visualization
- Color nodes by testament (OT=blue, NT=red)
- Edge width represents similarity strength
- Interactive network exploration

---

#### Get Verse Recommendations
```
GET /api/analytics/verse-recommendations/?verse_id=100
GET /api/analytics/verse-recommendations/?verse_id=100&top_k=10
```

**Parameters:**
- `verse_id` (required): ID of the reference verse
- `top_k` (optional): Number of similar verses (default 5)

**Response:**
```json
{
  "reference_verse": {
    "id": 100,
    "reference": "John 3:16",
    "text": "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life."
  },
  "recommendations": [
    {
      "id": 456,
      "reference": "Romans 5:8",
      "text": "But God demonstrates his own love for us in this: While we were still sinners, Christ died for us.",
      "similarity": 0.92
    },
    {
      "id": 789,
      "reference": "1 John 4:8",
      "text": "Whoever does not love does not know God, because God is love.",
      "similarity": 0.88
    },
    {
      "id": 234,
      "reference": "John 15:12",
      "text": "My command is this: Love each other as I have loved you.",
      "similarity": 0.85
    },
    {
      "id": 567,
      "reference": "Ephesians 3:17",
      "text": "...and I pray that you, being rooted and established in love...",
      "similarity": 0.81
    },
    {
      "id": 890,
      "reference": "Colossians 3:14",
      "text": "And over all these virtues put on love, which binds them all together in perfect unity.",
      "similarity": 0.79
    }
  ]
}
```

**Use Cases:**
- Show "related verses" in a study app
- Build topical pathways through scripture
- Find parallel passages across books
- Content recommendation for users

---

## Documentation

### Interactive API Documentation
```
GET /api/docs/          Swagger UI (try out endpoints here!)
GET /api/schema/        OpenAPI JSON schema
```

### File Documentation
```
FEATURES_IMPLEMENTATION.md       Full technical documentation
IMPLEMENTATION_SUMMARY.md        Overview and assessment value
API_DEMO.py                      Example usage script
QUICKSTART.sh                    Setup and server start
```

---

## Summary Statistics

### Total Endpoints
- **Read-only:** 8 endpoints
- **Full CRUD:** 7 endpoints (themes, theme-keywords, collections)
- **Analytics:** 5 endpoints (book-summaries, theme-coverage, similarity-graph, verse-recommendations)
- **Total:** 20+ HTTP endpoints

### HTTP Methods Supported
- ✅ GET (Read)
- ✅ POST (Create)
- ✅ PUT (Full Update)
- ✅ PATCH (Partial Update)
- ✅ DELETE (Remove)

### Response Formats
- ✅ JSON (all endpoints)
- ✅ Proper HTTP status codes
- ✅ Error messages with details
- ✅ Pagination support (list endpoints)
- ✅ Filter and search support

---

## Testing the API

### Using cURL
```bash
# List collections
curl http://localhost:8000/api/collections/

# Create a collection
curl -X POST http://localhost:8000/api/collections/ \
  -H "Content-Type: application/json" \
  -d '{"name":"My Collection","description":"Test","verses":[],"themes":[]}'

# Get similarity graph
curl "http://localhost:8000/api/analytics/similarity-graph/?threshold=0.5"

# Get verse recommendations
curl "http://localhost:8000/api/analytics/verse-recommendations/?verse_id=1&top_k=5"
```

### Using Python
```python
import requests

# Create collection
resp = requests.post(
    'http://localhost:8000/api/collections/',
    json={'name': 'My Collection', 'description': '', 'verses': [], 'themes': []}
)
print(resp.json())

# Get similarity graph
resp = requests.get('http://localhost:8000/api/analytics/similarity-graph/')
graph = resp.json()
print(f"Books: {len(graph['nodes'])}, Connections: {len(graph['edges'])}")
```

### Using the Demo Script
```bash
python API_DEMO.py
```

---

## Performance Considerations

### Optimizations in Place
- ✅ `prefetch_related()` for N+1 prevention
- ✅ `select_related()` for FK queries
- ✅ Caching layer for theme coverage
- ✅ Serializer design for efficient queries

### Potential Improvements
- Cache similarity matrix computation (Redis)
- Paginate large similarity graphs
- Add API rate limiting
- Compress JSON responses
