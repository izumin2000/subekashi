from django.db import migrations, models


def copy_song_to_songs(apps, schema_editor):
    """既存のFK(song)データをM2M(songs)に移行"""
    SongLink = apps.get_model('subekashi', 'SongLink')
    for link in SongLink.objects.filter(song__isnull=False).select_related('song'):
        link.songs.add(link.song)


class Migration(migrations.Migration):

    dependencies = [
        ('subekashi', '0032_alter_songlink_url'),
    ]

    operations = [
        # Step 1: M2Mフィールドを追加（related_name='+' で逆参照を一時的に無効化しFK競合を回避）
        migrations.AddField(
            model_name='songlink',
            name='songs',
            field=models.ManyToManyField(blank=True, related_name='+', to='subekashi.song'),
        ),
        # Step 2: データ移行（FK → M2M）
        migrations.RunPython(copy_song_to_songs, migrations.RunPython.noop),
        # Step 3: 旧FKを削除（related_name='links' が解放される）
        migrations.RemoveField(
            model_name='songlink',
            name='song',
        ),
        # Step 4: M2Mのrelated_nameを'links'に変更（DBスキーマ変更なし）
        migrations.AlterField(
            model_name='songlink',
            name='songs',
            field=models.ManyToManyField(blank=True, related_name='links', to='subekashi.song'),
        ),
    ]
