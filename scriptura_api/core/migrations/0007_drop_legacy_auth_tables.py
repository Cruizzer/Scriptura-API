from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_remove_collection_themes'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                'DROP TABLE IF EXISTS account_emailconfirmation;',
                'DROP TABLE IF EXISTS account_emailaddress;',
                'DROP TABLE IF EXISTS socialaccount_socialtoken;',
                'DROP TABLE IF EXISTS socialaccount_socialapp_sites;',
                'DROP TABLE IF EXISTS socialaccount_socialaccount;',
                'DROP TABLE IF EXISTS socialaccount_socialapp;',
                'DROP TABLE IF EXISTS authtoken_token;',
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
