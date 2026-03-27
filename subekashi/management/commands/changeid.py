from django.core.management.base import BaseCommand
from subekashi.models import Song

class Command(BaseCommand):
    def handle(self, *args, **options):
        old_id = options['id']
        new_id = options['to']

        song = Song.objects.get(pk=old_id)

        # M2M関係を変更前に保持
        imitate_targets = list(song.imitates.all())
        imitated_sources = list(song.imitateds.all())

        # 新IDで保存（INSERT）
        song.id = new_id
        song.save()

        # 新しいSongのM2M関係を設定
        new_song = Song.objects.get(pk=new_id)
        new_song.imitates.set(imitate_targets)
        for source in imitated_sources:
            source.imitates.add(new_song)

        # 旧IDを削除（M2M中間テーブルのold_id参照はCASCADEで削除）
        Song.objects.get(pk=old_id).delete()

    def add_arguments(self, parser):
        parser.add_argument('id', type=int)
        parser.add_argument('to', type=int)
