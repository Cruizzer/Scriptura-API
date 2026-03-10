from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from hashlib import sha256

from .models import BookSummary, ThemeCoverageCache, SimilarityCache
from .serializers import BookSummarySerializer

from themes.models import Theme
from core.models import Book, Verse
from analytics.services.text_analytics import TextAnalyticsService
from analytics.services.similarity_analytics import SimilarityAnalyticsService


class BookSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to precomputed analytics summaries."""
    queryset = BookSummary.objects.select_related('book').all()
    serializer_class = BookSummarySerializer

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        summary = self.get_object()
        return Response(BookSummarySerializer(summary).data)


class ThemeAnalyticsView(APIView):
    """Coverage of a theme's keywords across all books."""

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
    """
    Compute and return the book similarity graph.

    Query parameters:
        metric      "tfidf_cosine" (default) | "cosine" | "jaccard"
        threshold   float 0–1, default 0.3

    The graph is cached in the DB keyed on (book_set_hash, metric, threshold)
    so repeated requests are fast.  The cache is invalidated automatically
    when books are added or removed (the hash changes).

    The "testament" field on each node is one of:
        "Old"  Old Testament
        "New"  New Testament
    """

    VALID_METRICS = {'tfidf_cosine', 'cosine', 'jaccard'}

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
    """Top-k most similar verses to a given verse."""

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
    """Get recommendations for verses in a collection."""

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