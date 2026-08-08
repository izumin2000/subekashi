from django.db import migrations

QUESTIONABLE_SONG_IDS = [6570, 7989, 8000, 8012, 8016]


def set_is_questionable(apps, schema_editor):
    Song = apps.get_model('subekashi', 'Song')
    Song.objects.filter(id__in=QUESTIONABLE_SONG_IDS).update(is_questionable=True)


def unset_is_questionable(apps, schema_editor):
    Song = apps.get_model('subekashi', 'Song')
    Song.objects.filter(id__in=QUESTIONABLE_SONG_IDS).update(is_questionable=False)


class Migration(migrations.Migration):

    dependencies = [
        ('subekashi', '0036_song_is_questionable'),
    ]

    operations = [
        migrations.RunPython(set_is_questionable, unset_is_questionable),
    ]
