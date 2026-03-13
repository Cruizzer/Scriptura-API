from django.db import migrations


TRIGRAM_INDEX_NAME = 'core_verse_text_trgm_idx'


def create_pg_trgm_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    schema_editor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
    schema_editor.execute(
        f"CREATE INDEX IF NOT EXISTS {TRIGRAM_INDEX_NAME} "
        "ON core_verse USING gin (text gin_trgm_ops);"
    )


def drop_pg_trgm_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    schema_editor.execute(f'DROP INDEX IF EXISTS {TRIGRAM_INDEX_NAME};')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_collection_is_public'),
    ]

    operations = [
        migrations.RunPython(create_pg_trgm_index, reverse_code=drop_pg_trgm_index),
    ]
