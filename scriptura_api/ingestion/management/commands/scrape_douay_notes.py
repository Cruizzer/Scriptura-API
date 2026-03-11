import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


CHAPTER_RE = re.compile(r"^(.+?) Chapter (\d+)$")
VERSE_RE = re.compile(r"^(\d+):(\d+)[\.:]\s*(.*)$")
BOOK_TITLE_RE = re.compile(r"^THE BOOK OF\b")
FOOTNOTE_START_RE = re.compile(r"^[A-Za-z0-9\(\)\[\]\"'.,;:!?\- ]{1,120}\.\.\.\s*\S")


def normalize_space(lines: list[str]) -> str:
    return " ".join(part.strip() for part in lines if part.strip()).strip()


def ensure_slot(store: dict, book: str, chapter: int) -> None:
    store.setdefault(book, {})
    store[book].setdefault(str(chapter), {})


def parse_footnotes(input_path: Path) -> dict:
    bible: dict[str, dict[str, dict[str, dict[str, list[str] | str]]]] = {}

    book = None
    chapter = None
    verse = None

    verse_lines: list[str] = []
    note_lines: list[str] = []

    collecting_note = False
    prev_blank = True

    def flush_current() -> None:
        nonlocal verse_lines, note_lines
        if book is None or chapter is None or verse is None:
            verse_lines = []
            note_lines = []
            return

        note_text = normalize_space(note_lines)
        if not note_text:
            verse_lines = []
            note_lines = []
            return

        ensure_slot(bible, book, chapter)
        bible[book][str(chapter)][str(verse)] = {
            "text": normalize_space(verse_lines),
            "notes": [note_text],
        }

        verse_lines = []
        note_lines = []

    with input_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.strip()

            if not stripped:
                prev_blank = True
                continue

            chapter_match = CHAPTER_RE.match(stripped)
            if chapter_match:
                flush_current()
                book = chapter_match.group(1).strip()
                chapter = int(chapter_match.group(2))
                verse = None
                verse_lines = []
                note_lines = []
                collecting_note = False
                prev_blank = False
                continue

            if BOOK_TITLE_RE.match(stripped):
                flush_current()
                verse = None
                verse_lines = []
                note_lines = []
                collecting_note = False
                prev_blank = False
                continue

            verse_match = VERSE_RE.match(stripped)
            if verse_match:
                flush_current()
                verse = int(verse_match.group(2))
                verse_lines = [verse_match.group(3).strip()]
                note_lines = []
                collecting_note = False
                prev_blank = False
                continue

            if book is None or chapter is None or verse is None:
                prev_blank = False
                continue

            if collecting_note:
                note_lines.append(stripped)
                prev_blank = False
                continue

            if prev_blank and FOOTNOTE_START_RE.match(stripped):
                collecting_note = True
                note_lines.append(stripped)
            else:
                verse_lines.append(stripped)

            prev_blank = False

    flush_current()
    return bible


class Command(BaseCommand):
    help = 'Extract Douay-Rheims verse footnotes from pg8300 text into JSON.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            default='pg8300.txt',
            help='Path to source text file.',
        )
        parser.add_argument(
            '--output',
            default='douay_notes_scraped.json',
            help='Output JSON path.',
        )

    def handle(self, *args, **options):
        input_path = Path(options['input'])
        output_path = Path(options['output'])

        if not input_path.exists():
            raise CommandError(f'Input file not found: {input_path}')

        data = parse_footnotes(input_path)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

        self.stdout.write(self.style.SUCCESS(
            f'Wrote {output_path} with {len(data)} books.'
        ))
