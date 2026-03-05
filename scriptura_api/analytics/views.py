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
        "OT"  Old Testament
        "NT"  New Testament
        "DC"  Deuterocanonical (Tobit, Judith, 1-2 Macc, Wisdom, Sirach, Baruch)

    This lets the frontend render three distinct node colours.
    """

    def get(self, request):
        metric = request.query_params.get('metric', 'tfidf_cosine')
        try:
            threshold = float(request.query_params.get('threshold', 0.3))
            threshold = max(0.0, min(1.0, threshold))
        except (ValueError, TypeError):
            threshold = 0.3

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
            return Response(cached.graph_data)
        except SimilarityCache.DoesNotExist:
            pass

        # ── Compute ──────────────────────────────────────────────────────
        graph_data = SimilarityAnalyticsService.build_similarity_graph(
            books,
            similarity_threshold=threshold,
            metric=metric,
        )

        # ── Store ────────────────────────────────────────────────────────
        SimilarityCache.objects.update_or_create(
            book_set_hash=book_hash,
            metric=metric,
            threshold=threshold,
            defaults={'graph_data': graph_data},
        )

        return Response(graph_data)


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