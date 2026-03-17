from django.db import migrations, models
import django.db.models.deletion


def copy_song_to_songs(apps, schema_editor):
    """既存のFK(song)データをM2M(songs)に移行"""
    SongLink = apps.get_model('subekashi', 'SongLink')
    for link in SongLink.objects.filter(song__isnull=False).select_related('song'):
        link.songs.add(link.song)


class Migration(migrations.Migration):

    replaces = [
        ('subekashi', '0031_songlink_allow_dup_songlink_is_removed_and_more'),
        ('subekashi', '0032_alter_songlink_url'),
        ('subekashi', '0033_songlink_songs_m2m'),
        ('subekashi', '0034_alter_songlink_songs'),
    ]

    dependencies = [
        ('subekashi', '0030_song_islimited'),
    ]

    operations = [
        # FKをnullableにしてデータ移行に備える
        migrations.AlterField(
            model_name='songlink',
            name='song',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='links', to='subekashi.song'),
        ),
        migrations.AddField(
            model_name='songlink',
            name='allow_dup',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='songlink',
            name='is_removed',
            field=models.BooleanField(default=False),
        ),
        # M2Mフィールドを追加（related_name='+' でFK競合を回避）
        migrations.AddField(
            model_name='songlink',
            name='songs',
            field=models.ManyToManyField(blank=True, related_name='+', to='subekashi.song'),
        ),
        # データ移行（FK → M2M）
        migrations.RunPython(copy_song_to_songs, migrations.RunPython.noop),
        # 旧FKを削除
        migrations.RemoveField(
            model_name='songlink',
            name='song',
        ),
        # urlフィールドをURLField(unique=True)に更新
        migrations.AlterField(
            model_name='songlink',
            name='url',
            field=models.URLField(max_length=500, unique=True),
        ),
        # M2Mのrelated_nameを'links'に変更
        migrations.AlterField(
            model_name='songlink',
            name='songs',
            field=models.ManyToManyField(blank=True, related_name='links', to='subekashi.Song'),
        ),
    ]
