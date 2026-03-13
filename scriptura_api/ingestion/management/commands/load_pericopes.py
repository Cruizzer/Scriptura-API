"""
Load pericope (thematic section) headings from PericopeGroupedKJVVerses.json
and create Section records in the database.
"""
import json
import re
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Book, Chapter, Section


BULK_CREATE_BATCH_SIZE = 1000


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

        book_lookup = {}
        for book in Book.objects.only("id", "name"):
            book_lookup[book.name.lower()] = book.id
            book_lookup[book.name.replace(" ", "").lower()] = book.id

        referenced_chapters = set()
        resolved_pericopes = []

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
            book_id = book_lookup.get(book_name.lower()) or book_lookup.get(book_name.replace(" ", "").lower())
            if not book_id:
                self.stdout.write(
                    self.style.WARNING(
                        f"Book not found: {book_name} "
                        f"(Pericope: {pericope_title})"
                    )
                )
                error_count += 1
                continue

            referenced_chapters.add((book_id, chapter_num))
            resolved_pericopes.append((book_name, chapter_num, verse_num, pericope_title, i))

            # Progress indicator every 500 records
            if (i + 1) % 500 == 0:
                self.stdout.write(f"Processed {i + 1} pericopes...")

        chapter_lookup = {
            (chapter.book_id, chapter.number): chapter
            for chapter in Chapter.objects.filter(
                book_id__in={book_id for book_id, _ in referenced_chapters},
                number__in={chapter_num for _, chapter_num in referenced_chapters},
            ).only("id", "book_id", "number")
        }

        chapter_ids = [chapter.id for chapter in chapter_lookup.values()]
        existing_sections = {
            (section.chapter_id, section.start_verse): section
            for section in Section.objects.filter(chapter_id__in=chapter_ids).only("id", "chapter_id", "start_verse", "title")
        }

        sections_to_create = []
        sections_to_update = []
        seen_new_sections = set()

        with transaction.atomic():
            for book_name, chapter_num, verse_num, pericope_title, _ in resolved_pericopes:
                book_id = book_lookup.get(book_name.lower()) or book_lookup.get(book_name.replace(" ", "").lower())
                chapter = chapter_lookup.get((book_id, chapter_num))
                if not chapter:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Chapter not found: {book_name} {chapter_num} "
                            f"(Pericope: {pericope_title})"
                        )
                    )
                    error_count += 1
                    continue

                section_key = (chapter.id, verse_num)
                existing_section = existing_sections.get(section_key)
                if existing_section:
                    if existing_section.title != pericope_title:
                        existing_section.title = pericope_title
                        sections_to_update.append(existing_section)
                    created_count += 1
                    continue

                if section_key in seen_new_sections:
                    created_count += 1
                    continue

                seen_new_sections.add(section_key)
                sections_to_create.append(Section(
                    chapter_id=chapter.id,
                    start_verse=verse_num,
                    title=pericope_title,
                ))
                created_count += 1

            if sections_to_create:
                Section.objects.bulk_create(sections_to_create, batch_size=BULK_CREATE_BATCH_SIZE)

            if sections_to_update:
                Section.objects.bulk_update(sections_to_update, ["title"], batch_size=BULK_CREATE_BATCH_SIZE)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nPericope import complete: {created_count} sections created, "
                f"{skipped_count} skipped, {error_count} errors"
            )
        )
