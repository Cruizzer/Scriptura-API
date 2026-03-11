import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.models import Book, Chapter, Verse, Footnote


BOOK_ALIASES = {
    'Josue': 'Joshua',
    '1 Kings': '1 Samuel',
    '2 Kings': '2 Samuel',
    '3 Kings': '1 Kings',
    '4 Kings': '2 Kings',
    '1 Paralipomenon': '1 Chronicles',
    '2 Paralipomenon': '2 Chronicles',
    '1 Esdras': 'Ezra',
    '2 Esdras': 'Nehemiah',
    'Tobias': 'Tobit',
    'Canticle of Canticles': 'Song of Solomon',
    'Wisdom': 'Wisdom of Solomon',
    'Ecclesiasticus': 'Sirach',
    'Isaias': 'Isaiah',
    'Jeremias': 'Jeremiah',
    'Ezechiel': 'Ezekiel',
    'Osee': 'Hosea',
    'Abdias': 'Obadiah',
    'Jonas': 'Jonah',
    'Micheas': 'Micah',
    'Habacuc': 'Habakkuk',
    'Sophonias': 'Zephaniah',
    'Aggeus': 'Haggai',
    'Zacharias': 'Zechariah',
    'Malachias': 'Malachi',
    '1 Machabees': '1 Maccabees',
    '2 Machabees': '2 Maccabees',
    'Apocalypse': 'Revelation',
}


class Command(BaseCommand):
    help = 'Load scraped Douay notes JSON into Footnote records.'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to douay_notes_scraped.json file',
        )
        parser.add_argument(
            '--replace-existing',
            action='store_true',
            help='Delete previously imported Douay notes (marker DR*) before importing.',
        )

    def handle(self, *args, **options):
        json_path = Path(options['json_file'])
        if not json_path.exists():
            raise CommandError(f'JSON file not found: {json_path}')

        try:
            data = json.loads(json_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'Invalid JSON in {json_path}: {exc}') from exc

        if options.get('replace_existing'):
            deleted, _ = Footnote.objects.filter(marker__startswith='DR').delete()
            self.stdout.write(f'Removed {deleted} existing Douay note records.')

        books = {b.name.lower(): b for b in Book.objects.all()}

        created = 0
        skipped_books = 0
        skipped_chapters = 0
        skipped_verses = 0
        skipped_notes = 0

        for src_book_name, chapter_payload in data.items():
            target_book_name = BOOK_ALIASES.get(src_book_name, src_book_name)
            book = books.get(target_book_name.lower())

            if not book:
                skipped_books += 1
                self.stdout.write(self.style.WARNING(f'Book not found: {src_book_name} -> {target_book_name}'))
                continue

            chapter_numbers = []
            for ch_raw in chapter_payload.keys():
                try:
                    chapter_numbers.append(int(ch_raw))
                except (TypeError, ValueError):
                    continue

            chapters = {
                ch.number: ch
                for ch in Chapter.objects.filter(book=book, number__in=chapter_numbers)
            }

            for ch_raw, verse_payload in chapter_payload.items():
                try:
                    chapter_number = int(ch_raw)
                except (TypeError, ValueError):
                    skipped_chapters += 1
                    continue

                chapter = chapters.get(chapter_number)
                if not chapter:
                    skipped_chapters += 1
                    continue

                verse_map = {
                    v.number: v
                    for v in Verse.objects.filter(chapter=chapter).only('id', 'number')
                }

                for verse_raw, verse_obj in verse_payload.items():
                    try:
                        verse_number = int(verse_raw)
                    except (TypeError, ValueError):
                        skipped_verses += 1
                        continue

                    verse = verse_map.get(verse_number)
                    if not verse:
                        skipped_verses += 1
                        continue

                    notes = verse_obj.get('notes') or []
                    if not isinstance(notes, list):
                        skipped_notes += 1
                        continue

                    for idx, note_text in enumerate(notes, start=1):
                        clean_text = ' '.join(str(note_text).split()).strip()
                        if not clean_text:
                            skipped_notes += 1
                            continue

                        marker = 'DR' if len(notes) == 1 else f'DR{idx}'
                        _, was_created = Footnote.objects.get_or_create(
                            verse=verse,
                            marker=marker,
                            text=clean_text,
                        )
                        if was_created:
                            created += 1

        self.stdout.write(self.style.SUCCESS(
            'Douay note import complete: '
            f'{created} footnotes created, '
            f'{skipped_books} books skipped, '
            f'{skipped_chapters} chapters skipped, '
            f'{skipped_verses} verses skipped, '
            f'{skipped_notes} notes skipped.'
        ))
