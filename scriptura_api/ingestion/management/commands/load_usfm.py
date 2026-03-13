import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from analytics.models import BookSummary
from analytics.services.text_analytics import TextAnalyticsService
from core.models import Book, Chapter, Verse, Section, Footnote


VERSE_PATTERN = re.compile(r'^\\v\s+(\d+[a-z]?)\s*(.*)$')
CHAPTER_PATTERN = re.compile(r'^\\c\s+(\d+)')
SECTION_PATTERN = re.compile(r'^\\s\d*\s+(.*)$')
WORD_TAG_PATTERN = re.compile(r'\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*')
BULK_CREATE_BATCH_SIZE = 1000


class Command(BaseCommand):
    help = 'Load Bible content from a USFM directory (supports paragraphs, section headings, and footnotes).'

    def add_arguments(self, parser):
        parser.add_argument('usfm_dir', type=str, help='Path to directory containing .usfm files')
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing Book/Chapter/Verse/Section/Footnote data before importing'
        )

    def handle(self, *args, **options):
        usfm_dir = Path(options['usfm_dir'])
        if not usfm_dir.exists() or not usfm_dir.is_dir():
            raise CommandError(f'USFM directory not found: {usfm_dir}')

        files = sorted(usfm_dir.glob('*.usfm'))
        if not files:
            raise CommandError(f'No .usfm files found in: {usfm_dir}')

        with transaction.atomic():
            if options['reset']:
                self.stdout.write('Resetting existing scripture data...')
                Footnote.objects.all().delete()
                Section.objects.all().delete()
                Verse.objects.all().delete()
                Chapter.objects.all().delete()
                Book.objects.all().delete()
                BookSummary.objects.all().delete()

            imported_books = 0
            imported_chapters = 0
            imported_verses = 0
            imported_sections = 0
            imported_footnotes = 0

            for usfm_file in files:
                stats = self._import_usfm_file(usfm_file)
                imported_books += stats['books']
                imported_chapters += stats['chapters']
                imported_verses += stats['verses']
                imported_sections += stats['sections']
                imported_footnotes += stats['footnotes']

        self.stdout.write(self.style.SUCCESS(
            'USFM import complete: '
            f'{imported_books} books, '
            f'{imported_chapters} chapters, '
            f'{imported_verses} verses, '
            f'{imported_sections} sections, '
            f'{imported_footnotes} footnotes'
        ))

    def _import_usfm_file(self, usfm_path: Path):
        lines = usfm_path.read_text(encoding='utf-8').splitlines()

        book_name = None
        current_book = None
        current_chapter = None
        current_verse = None

        pending_section_title = None
        next_paragraph_start = True

        created_book = 0
        created_chapters = 0
        created_verses = 0
        created_sections = 0
        created_footnotes = 0

        cumulative_text = []
        verses_to_create = []
        sections_to_create = []
        footnotes_to_create = []

        testament = self._testament_from_filename(usfm_path.name)

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Book title
            if line.startswith('\\h '):
                book_name = line[3:].strip()
                continue

            # Chapter marker
            chapter_match = CHAPTER_PATTERN.match(line)
            if chapter_match:
                chapter_number = int(chapter_match.group(1))

                if current_book is None:
                    if not book_name:
                        book_name = self._book_name_from_filename(usfm_path.name)

                    current_book, was_created = Book.objects.get_or_create(
                        name=book_name,
                        defaults={'testament': testament}
                    )
                    created_book += 1 if was_created else 0

                current_chapter, was_created = Chapter.objects.get_or_create(
                    book=current_book,
                    number=chapter_number
                )
                created_chapters += 1 if was_created else 0

                current_verse = None
                pending_section_title = None
                next_paragraph_start = True
                continue

            # Section title markers (if present)
            section_match = SECTION_PATTERN.match(line)
            if section_match:
                pending_section_title = section_match.group(1).strip()
                continue

            # Paragraph markers for next verse
            if re.match(r'^\\(p|m|pi\d*|q\d*|b)\b', line):
                next_paragraph_start = True
                continue

            # Verse line
            verse_match = VERSE_PATTERN.match(line)
            if verse_match:
                if current_chapter is None:
                    continue

                verse_num_raw = verse_match.group(1)
                verse_number = self._parse_verse_number(verse_num_raw)
                verse_text_raw = verse_match.group(2).strip()

                clean_text, footnotes = self._clean_text_and_extract_footnotes(verse_text_raw)

                current_verse = Verse(
                    chapter=current_chapter,
                    number=verse_number,
                    text=clean_text,
                    paragraph_start=next_paragraph_start,
                )
                verses_to_create.append(current_verse)
                created_verses += 1
                cumulative_text.append(clean_text)
                next_paragraph_start = False

                if pending_section_title:
                    sections_to_create.append(Section(
                        chapter=current_chapter,
                        start_verse=verse_number,
                        title=pending_section_title
                    ))
                    created_sections += 1
                    pending_section_title = None

                for fn in footnotes:
                    footnotes_to_create.append(Footnote(
                        verse=current_verse,
                        marker=fn['marker'],
                        text=fn['text']
                    ))
                    created_footnotes += 1

                continue

            # Continuation text line (append to latest verse)
            if current_verse is not None and not line.startswith('\\'):
                clean_text, footnotes = self._clean_text_and_extract_footnotes(line)
                if clean_text:
                    current_verse.text = f"{current_verse.text} {clean_text}".strip()
                for fn in footnotes:
                    footnotes_to_create.append(Footnote(
                        verse=current_verse,
                        marker=fn['marker'],
                        text=fn['text']
                    ))
                    created_footnotes += 1

        if verses_to_create:
            Verse.objects.bulk_create(verses_to_create, batch_size=BULK_CREATE_BATCH_SIZE)

        if sections_to_create:
            Section.objects.bulk_create(sections_to_create, batch_size=BULK_CREATE_BATCH_SIZE)

        if footnotes_to_create:
            Footnote.objects.bulk_create(footnotes_to_create, batch_size=BULK_CREATE_BATCH_SIZE)

        # update summary for this book
        if current_book and cumulative_text:
            full_text = ' '.join(cumulative_text)
            BookSummary.objects.update_or_create(
                book=current_book,
                defaults={
                    'word_count': TextAnalyticsService.word_count(full_text),
                    'entropy': TextAnalyticsService.entropy(full_text),
                    'ttr': TextAnalyticsService.type_token_ratio(full_text),
                    'hapax_count': TextAnalyticsService.hapax_legomena(full_text),
                }
            )

        return {
            'books': created_book,
            'chapters': created_chapters,
            'verses': created_verses,
            'sections': created_sections,
            'footnotes': created_footnotes,
        }

    def _clean_text_and_extract_footnotes(self, text: str):
        footnotes = []

        # Extract \f ... \f* footnote blocks if present
        while True:
            start = text.find('\\f ')
            if start == -1:
                break
            end = text.find('\\f*', start)
            if end == -1:
                break

            block = text[start:end + 3]
            marker_match = re.search(r'\\f\s+([^\s\\]+)', block)
            marker = marker_match.group(1) if marker_match else ''

            body = re.sub(r'^\\f\s+[^\s\\]+\s*', '', block)
            body = body.replace('\\f*', '')
            body = re.sub(r'\\[a-z0-9*]+\s*', ' ', body)
            body = re.sub(r'\s+', ' ', body).strip()

            footnotes.append({'marker': marker, 'text': body})
            text = text[:start] + text[end + 3:]

        # Convert USFM word tags into plain words
        text = WORD_TAG_PATTERN.sub(lambda m: m.group(1).strip(), text)

        # Remove remaining inline markers
        text = re.sub(r'\\[a-z0-9]+\*?', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text, footnotes

    def _parse_verse_number(self, verse_raw: str) -> int:
        match = re.match(r'\d+', verse_raw)
        return int(match.group(0)) if match else 0

    def _testament_from_filename(self, filename: str) -> str:
        leading = filename.split('-')[0]
        try:
            book_no = int(leading)
            return 'New' if book_no >= 70 else 'Old'
        except ValueError:
            return 'Old'

    def _book_name_from_filename(self, filename: str) -> str:
        code = filename.split('engDRA')[0].split('-')[-1]
        code_map = {
            'GEN': 'Genesis', 'EXO': 'Exodus', 'LEV': 'Leviticus', 'NUM': 'Numbers', 'DEU': 'Deuteronomy',
            'JOS': 'Joshua', 'JDG': 'Judges', 'RUT': 'Ruth', '1SA': 'I Samuel', '2SA': 'II Samuel',
            '1KI': 'I Kings', '2KI': 'II Kings', '1CH': 'I Chronicles', '2CH': 'II Chronicles',
            'EZR': 'Ezra', 'NEH': 'Nehemiah', 'EST': 'Esther', 'JOB': 'Job', 'PSA': 'Psalms',
            'PRO': 'Proverbs', 'ECC': 'Ecclesiastes', 'SNG': 'Song of Solomon', 'ISA': 'Isaiah',
            'JER': 'Jeremiah', 'LAM': 'Lamentations', 'EZK': 'Ezekiel', 'DAN': 'Daniel',
            'HOS': 'Hosea', 'JOL': 'Joel', 'AMO': 'Amos', 'OBA': 'Obadiah', 'JON': 'Jonah',
            'MIC': 'Micah', 'NAM': 'Nahum', 'HAB': 'Habakkuk', 'ZEP': 'Zephaniah', 'HAG': 'Haggai',
            'ZEC': 'Zechariah', 'MAL': 'Malachi', 'TOB': 'Tobit', 'JDT': 'Judith', 'WIS': 'Wisdom',
            'SIR': 'Sirach', 'BAR': 'Baruch', '1MA': 'I Maccabees', '2MA': 'II Maccabees',
            'MAT': 'Matthew', 'MRK': 'Mark', 'LUK': 'Luke', 'JHN': 'John', 'ACT': 'Acts',
            'ROM': 'Romans', '1CO': 'I Corinthians', '2CO': 'II Corinthians', 'GAL': 'Galatians',
            'EPH': 'Ephesians', 'PHP': 'Philippians', 'COL': 'Colossians', '1TH': 'I Thessalonians',
            '2TH': 'II Thessalonians', '1TI': 'I Timothy', '2TI': 'II Timothy', 'TIT': 'Titus',
            'PHM': 'Philemon', 'HEB': 'Hebrews', 'JAS': 'James', '1PE': 'I Peter', '2PE': 'II Peter',
            '1JN': 'I John', '2JN': 'II John', '3JN': 'III John', 'JUD': 'Jude', 'REV': 'Revelation of John'
        }
        return code_map.get(code, code)
