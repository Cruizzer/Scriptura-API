from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from django.shortcuts import get_object_or_404
from hashlib import sha256

from .models import BookSummary, ThemeCoverageCache, SimilarityCache
from .serializers import BookSummarySerializer

from themes.models import Theme
from core.models import Book, Verse
from analytics.services.text_analytics import TextAnalyticsService
from analytics.services.similarity_analytics import SimilarityAnalyticsService


@extend_schema_view(
    list=extend_schema(
        summary="List book analytics summaries",
        description=(
            "Returns precomputed linguistic statistics for every book of the Bible.\n\n"
            "Fields include: `word_count`, `vocab_size`, `type_token_ratio` (lexical richness), "
            "`entropy` (information density), and `hapax_count` (words appearing exactly once).\n\n"
            "**Authentication:** not required."
        ),
        tags=['Analytics'],
    ),
    retrieve=extend_schema(
        summary="Get analytics for one book",
        description=(
            "Returns the full precomputed analytics record for a single book identified "
            "by its `book_summary_id`.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter('id', int, OpenApiParameter.PATH,
                             description='Primary key of the BookSummary record (use the `id` '
                                         'field from `GET /api/book-summaries/`).')
        ],
        tags=['Analytics'],
    ),
)
class BookSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Precomputed linguistic analytics for each book of the Bible."""
    queryset = BookSummary.objects.select_related('book').all()
    serializer_class = BookSummarySerializer


class ThemeAnalyticsView(APIView):
    """Keyword coverage analysis for a single theme across all books."""

    @staticmethod
    def _keyword_signature(words):
        normalized = sorted(w.strip().lower() for w in words if w and w.strip())
        return sha256("|".join(normalized).encode('utf-8')).hexdigest()

    @staticmethod
    def _compute_coverage(keywords):
        coverage = []
        for book in Book.objects.prefetch_related('chapters__verses').all():
            text = " ".join(
                v.text for c in book.chapters.all() for v in c.verses.all()
            ).lower()
            freq = TextAnalyticsService.word_frequency(text)
            count = sum(freq.get(k, 0) for k in keywords)
            coverage.append({"book": book.name, "keyword_count": count})
        return coverage

    @extend_schema(
        summary="Theme keyword occurrences by book",
        description=(
            "For the theme identified by `id`, returns how often each of its "
            "keywords appears in every book of the Bible.\n\n"
            "Results are cached — the first call may be slower. The cache is "
            "automatically invalidated if the theme's keyword list changes.\n\n"
            "**Authentication:** not required."
        ),
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'theme_id':    {'type': 'integer'},
                    'theme':       {'type': 'string'},
                    'keywords':    {'type': 'array', 'items': {'type': 'string'}},
                    'occurrences': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'book':          {'type': 'string'},
                                'keyword_count': {'type': 'integer'},
                            }
                        }
                    },
                }
            },
            404: OpenApiTypes.OBJECT,
        },
        tags=['Analytics'],
    )
    def get(self, request, pk):
        theme = get_object_or_404(Theme.objects.prefetch_related('keywords'), pk=pk)
        keyword_words = [kw.word for kw in theme.keywords.all()]
        keywords = [w.lower() for w in keyword_words]
        signature = self._keyword_signature(keyword_words)

        cache = getattr(theme, 'coverage_cache', None)
        if cache and cache.keyword_signature == signature:
            coverage = cache.coverage
        else:
            coverage = self._compute_coverage(keywords)
            ThemeCoverageCache.objects.update_or_create(
                theme=theme,
                defaults={'keyword_signature': signature, 'coverage': coverage},
            )

        return Response({
            "theme_id": theme.id,
            "theme": theme.name,
            "keywords": keyword_words,
            "occurrences": coverage,
        })


class LexicalSimilarityGraphView(APIView):
    """Compute and return a book-similarity network graph."""

    VALID_METRICS = {'tfidf_cosine', 'cosine', 'jaccard'}

    @extend_schema(
        summary="Book lexical similarity graph",
        description=(
            "Returns a network graph where **nodes** are biblical books and **edges** "
            "connect books whose text similarity exceeds `threshold`.\n\n"
            "Also returns summary statistics: graph density, average edge weight, and "
            "the five most-connected books.\n\n"
            "Results are cached — the first call for a given `metric` + `threshold` "
            "combination may be slow.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter(
                'metric', str, OpenApiParameter.QUERY,
                description='Similarity algorithm to use.',
                enum=['tfidf_cosine', 'cosine', 'jaccard'],
                default='tfidf_cosine',
                required=False,
            ),
            OpenApiParameter(
                'threshold', float, OpenApiParameter.QUERY,
                description='Minimum similarity score (0–1) for an edge to be included. Default: `0.3`.',
                required=False,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
        tags=['Analytics'],
    )

    def get(self, request):
        metric = request.query_params.get('metric', 'tfidf_cosine')

        if metric not in self.VALID_METRICS:
            return Response(
                {
                    "error": f"Invalid metric '{metric}'.",
                    "valid_metrics": sorted(self.VALID_METRICS),
                },
                status=400,
            )

        try:
            threshold = float(request.query_params.get('threshold', 0.3))
            threshold = max(0.0, min(1.0, threshold))
        except (ValueError, TypeError):
            return Response(
                {"error": "threshold must be a number between 0.0 and 1.0."},
                status=400,
            )

        # Round threshold to 2 dp so that 0.30000000001 doesn't create a
        # separate cache row from 0.3.
        threshold = round(threshold, 2)

        # Fast cache key check: only book IDs are needed for the hash.
        books_for_hash = Book.objects.only('id')

        # ── Cache check ──────────────────────────────────────────────────
        book_hash = SimilarityAnalyticsService.book_set_hash(books_for_hash)
        try:
            cached = SimilarityCache.objects.get(
                book_set_hash=book_hash,
                metric=metric,
                threshold=threshold,
            )
            graph_data = cached.graph_data
        except SimilarityCache.DoesNotExist:
            books = Book.objects.prefetch_related('chapters__verses').all()
            # ── Compute ──────────────────────────────────────────────────
            graph_data = SimilarityAnalyticsService.build_similarity_graph(
                books,
                similarity_threshold=threshold,
                metric=metric,
            )
            # ── Store ────────────────────────────────────────────────────
            SimilarityCache.objects.update_or_create(
                book_set_hash=book_hash,
                metric=metric,
                threshold=threshold,
                defaults={'graph_data': graph_data},
            )

        # ── Summary stats (computed on every request, not stored in cache) ──
        book_count = books_for_hash.count()
        edge_count = len(graph_data['edges'])
        max_possible_edges = book_count * (book_count - 1) // 2

        degree: dict = {}
        for edge in graph_data['edges']:
            degree[edge['source']] = degree.get(edge['source'], 0) + 1
            degree[edge['target']] = degree.get(edge['target'], 0) + 1

        most_connected = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:5]

        weights = [e['weight'] for e in graph_data['edges']]

        summary = {
            "book_count": book_count,
            "edge_count": edge_count,
            "max_possible_edges": max_possible_edges,
            "graph_density": round(edge_count / max_possible_edges, 4) if max_possible_edges else 0,
            "avg_edge_weight": round(sum(weights) / len(weights), 4) if weights else 0,
            "most_connected": [
                {"book": book, "connections": deg} for book, deg in most_connected
            ],
        }

        response = Response({"summary": summary, **graph_data})

        # Cache aggressively at browser + CDN for the default graph URL.
        if metric == 'tfidf_cosine' and threshold == 0.3:
            response['Cache-Control'] = 'public, max-age=86400, s-maxage=86400, stale-while-revalidate=604800, immutable'
        else:
            response['Cache-Control'] = 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400'

        return response


class VerseRecommendationView(APIView):
    """Find verses most semantically similar to a reference verse."""

    @extend_schema(
        summary="Verse similarity recommendations",
        description=(
            "Given a `verse_id`, returns the `top_k` most semantically similar verses "
            "from across the entire Bible, ranked by TF-IDF cosine similarity.\n\n"
            "Use `GET /api/verses/` to find verse IDs.\n\n"
            "**Authentication:** not required."
        ),
        parameters=[
            OpenApiParameter(
                'verse_id', int, OpenApiParameter.QUERY,
                description='Primary key of the reference verse (required).',
                required=True,
            ),
            OpenApiParameter(
                'top_k', int, OpenApiParameter.QUERY,
                description='Number of similar verses to return. Default: `5`.',
                required=False,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=['Analytics'],
    )

    def get(self, request):
        verse_id = request.query_params.get('verse_id')
        if not verse_id:
            return Response({"error": "verse_id parameter is required"}, status=400)

        try:
            verse = Verse.objects.select_related('chapter__book').get(id=verse_id)
        except Verse.DoesNotExist:
            return Response({"error": f"Verse {verse_id} not found"}, status=404)

        try:
            top_k = max(1, int(request.query_params.get('top_k', 5)))
        except (ValueError, TypeError):
            top_k = 5

        all_verses = Verse.objects.select_related('chapter__book').all()
        recommendations = SimilarityAnalyticsService.find_similar_verses(
            verse.text, all_verses, top_k=top_k
        )

        return Response({
            "reference_verse": {
                "id": verse.id,
                "reference": f"{verse.chapter.book.name} {verse.chapter.number}:{verse.number}",
                "text": verse.text,
            },
            "recommendations": recommendations,
        })


class CollectionRecommendationsView(APIView):
    """Recommend new verses based on the verses already in a collection."""

    @extend_schema(
        summary="Collection-based verse recommendations",
        description=(
            "Aggregates TF-IDF cosine similarities across all verses in a collection "
            "and returns the `top_k` verses (not already in the collection) that are "
            "most thematically related.\n\n"
            "Use `GET /api/collections/` to find collection IDs.\n\n"
            "**Authentication:** not required (public collections only for unauthenticated callers)."
        ),
        parameters=[
            OpenApiParameter(
                'collection_id', int, OpenApiParameter.QUERY,
                description='Primary key of the collection (required).',
                required=True,
            ),
            OpenApiParameter(
                'top_k', int, OpenApiParameter.QUERY,
                description='Number of recommendations to return. Default: `5`.',
                required=False,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=['Analytics'],
    )

    def get(self, request):
        from core.models import Collection
        
        collection_id = request.query_params.get('collection_id')
        if not collection_id:
            return Response({"error": "collection_id parameter is required"}, status=400)

        try:
            collection = Collection.objects.prefetch_related('verses').get(id=collection_id)
        except Collection.DoesNotExist:
            return Response({"error": f"Collection {collection_id} not found"}, status=404)

        try:
            top_k = max(1, int(request.query_params.get('top_k', 5)))
        except (ValueError, TypeError):
            top_k = 5

        # Get all verses in the collection
        collection_verses = list(collection.verses.all())
        if not collection_verses:
            return Response({
                "collection": {"id": collection.id, "name": collection.name},
                "verse_count": 0,
                "recommendations": []
            })

        # Get all verses for similarity search
        all_verses = Verse.objects.select_related('chapter__book').all()

        # Aggregate recommendations from all verses in the collection
        recommendation_scores = {}  # verse_id -> aggregated score
        recommendation_data = {}    # verse_id -> verse data

        for verse in collection_verses:
            recommendations = SimilarityAnalyticsService.find_similar_verses(
                verse.text, all_verses, top_k=top_k * 2  # Get more to have better aggregation
            )
            
            for rec in recommendations:
                rec_id = rec['id']
                # Skip if the recommended verse is already in the collection
                if rec_id in [v.id for v in collection_verses]:
                    continue
                    
                if rec_id not in recommendation_scores:
                    recommendation_scores[rec_id] = 0
                    recommendation_data[rec_id] = rec
                
                # Aggregate by adding similarity scores
                recommendation_scores[rec_id] += rec['similarity']

        # Sort by aggregated score and take top k
        sorted_recs = sorted(
            recommendation_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        final_recommendations = [
            {**recommendation_data[rec_id], 'aggregated_similarity': round(score, 4)}
            for rec_id, score in sorted_recs
        ]

        return Response({
            "collection": {"id": collection.id, "name": collection.name},
            "verse_count": len(collection_verses),
            "recommendations": final_recommendations
        })