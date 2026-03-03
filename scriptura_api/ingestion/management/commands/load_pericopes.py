"""
Load pericope (thematic section) headings from PericopeGroupedKJVVerses.json
and create Section records in the database.
"""
import json
import re
import os
from django.core.management.base import BaseCommand
from core.models import Book, Chapter, Section


class Command(BaseCommand):
    help = "Load pericope headings from JSON file and create Section records"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to PericopeGroupedKJVVerses.json file",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing Section records before importing",
        )

    def parse_reference(self, reference):
        """
        Parse a reference like "Genesis 1:1" into (book_name, chapter_num, verse_num)
        Returns tuple or None if parsing fails
        """
        # Pattern: BookName ChapterNumber:VerseNumber
        match = re.match(r"^(.+?)\s+(\d+):(\d+)$", reference.strip())
        if match:
            book_name = match.group(1)
            chapter_num = int(match.group(2))
            verse_num = int(match.group(3))
            return (book_name, chapter_num, verse_num)
        return None

    def get_book_id_by_name(self, book_name):
        """
        Look up book ID by name (handles variations like "1 John" vs "1John")
        """
        book = Book.objects.filter(name__iexact=book_name).first()
        if book:
            return book.id
        # Try without spaces
        book_name_no_space = book_name.replace(" ", "")
        book = Book.objects.filter(name__iexact=book_name_no_space).first()
        if book:
            return book.id
        return None

    def handle(self, *args, **options):
        json_file = options["json_file"]
        reset = options.get("reset", False)

        if not os.path.exists(json_file):
            self.stdout.write(
                self.style.ERROR(f"File not found: {json_file}")
            )
            return

        # Load JSON
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                pericopes = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f"Invalid JSON: {e}")
            )
            return

        # Reset if requested
        if reset:
            Section.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Deleted all existing Section records"))

        created_count = 0
        skipped_count = 0
        error_count = 0

        for i, pericope in enumerate(pericopes):
            pericope_title = pericope.get("Pericope", "").strip()
            ref_start = pericope.get("Reference Start", "").strip()

            if not pericope_title or not ref_start:
                skipped_count += 1
                continue

            # Parse the start reference
            parsed = self.parse_reference(ref_start)
            if not parsed:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not parse reference: {ref_start} "
                        f"(Pericope: {pericope_title})"
                    )
                )
                error_count += 1
                continue

            book_name, chapter_num, verse_num = parsed

            # Get book ID
            book_id = self.get_book_id_by_name(book_name)
            if not book_id:
                self.stdout.write(
                    self.style.WARNING(
                        f"Book not found: {book_name} "
                        f"(Pericope: {pericope_title})"
                    )
                )
                error_count += 1
                continue

            # Get chapter
            try:
                chapter = Chapter.objects.get(book_id=book_id, number=chapter_num)
            except Chapter.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Chapter not found: {book_name} {chapter_num} "
                        f"(Pericope: {pericope_title})"
                    )
                )
                error_count += 1
                continue

            # Create Section
            try:
                section, created = Section.objects.get_or_create(
                    chapter=chapter,
                    start_verse=verse_num,
                    defaults={"title": pericope_title},
                )
                if created:
                    created_count += 1
                else:
                    # Update title if it already existed
                    if section.title != pericope_title:
                        section.title = pericope_title
                        section.save()
                    created_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error creating section: {e} "
                        f"(Pericope: {pericope_title})"
                    )
                )
                error_count += 1

            # Progress indicator every 500 records
            if (i + 1) % 500 == 0:
                self.stdout.write(f"Processed {i + 1} pericopes...")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nPericope import complete: {created_count} sections created, "
                f"{skipped_count} skipped, {error_count} errors"
            )
        )
