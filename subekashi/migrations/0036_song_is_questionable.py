from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subekashi', '0035_rename_song_boolean_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='is_questionable',
            field=models.BooleanField(default=False),
        ),
    ]
