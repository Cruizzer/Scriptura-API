from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.types import OpenApiTypes
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
        description="List precomputed analytics summaries for all books"
    ),
    retrieve=extend_schema(
        description="Get detailed analytics for a specific book including word count, entropy, vocabulary richness, and hapax legomena"
    )
)
class BookSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to precomputed book analytics.
    
    Access linguistic statistics (entropy, type-token ratio, hapax count) for each book.
    **No authentication required.**
    """
    queryset = BookSummary.objects.select_related('book').all()
    serializer_class = BookSummarySerializer


class ThemeAnalyticsView(APIView):
    """Theme keyword coverage analysis.
    
    Analyze how keywords in a theme are distributed across all books.
    Returns keyword frequency for each book for the specified theme.
    **No authentication required.**
    """

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
        description="Get theme coverage showing keyword frequency across all books",
        parameters=[]
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

        return Response({"theme": theme.name, "coverage": coverage})


class LexicalSimilarityGraphView(APIView):
    """Book similarity network visualization.
    
    Compute and return a graph of semantic similarities between biblical books based on
    TF-IDF, cosine, or Jaccard similarity metrics. Results are cached automatically.
    
    Query parameters:
    - metric: "tfidf_cosine" (default) | "cosine" | "jaccard"
    - threshold: float 0–1, default 0.3 (minimum similarity to include edge)
    
    Returns nodes (books) and edges (similarities) forming a network graph, along with
    summary statistics (density, average weight, most-connected books).
    **No authentication required.**
    """

    VALID_METRICS = {'tfidf_cosine', 'cosine', 'jaccard'}

    @extend_schema(
        description="Get the book similarity graph with optional metric and threshold filtering",
        parameters=[
            {'name': 'metric', 'description': 'Similarity metric: tfidf_cosine, cosine, or jaccard', 'schema': {'type': 'string', 'default': 'tfidf_cosine'}},
            {'name': 'threshold', 'description': 'Minimum similarity to include edge (0-1)', 'schema': {'type': 'number', 'default': 0.3}},
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
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

        books = Book.objects.prefetch_related('chapters__verses').all()

        # ── Cache check ──────────────────────────────────────────────────
        book_hash = SimilarityAnalyticsService.book_set_hash(books)
        try:
            cached = SimilarityCache.objects.get(
                book_set_hash=book_hash,
                metric=metric,
                threshold=threshold,
            )
            graph_data = cached.graph_data
        except SimilarityCache.DoesNotExist:
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
        book_count = books.count()
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

        return Response({"summary": summary, **graph_data})


class VerseRecommendationView(APIView):
    """Find verses most similar to a reference verse.
    
    Given a verse ID, returns the top-k most semantically similar verses from the
    entire Bible using TF-IDF cosine similarity on verse text.
    
    **No authentication required.**
    """

    @extend_schema(
        description="Get verses most similar to a reference verse",
        parameters=[
            {'name': 'verse_id', 'description': 'The ID of the reference verse (required)', 'schema': {'type': 'integer'}},
            {'name': 'top_k', 'description': 'Number of recommendations to return (default 5)', 'schema': {'type': 'integer', 'default': 5}},
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
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
    """Get verse recommendations based on a collection.
    
    Given a collection ID, aggregates similarities from all verses in the collection
    and returns the top-k most similar verses not already in the collection.
    Useful for discovering thematically related verses.
    
    **No authentication required.**
    """

    @extend_schema(
        description="Get verses recommended based on similarity to a collection's verses",
        parameters=[
            {'name': 'collection_id', 'description': 'The ID of the collection (required)', 'schema': {'type': 'integer'}},
            {'name': 'top_k', 'description': 'Number of recommendations to return (default 5)', 'schema': {'type': 'integer', 'default': 5}},
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
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