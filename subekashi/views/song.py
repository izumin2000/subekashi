from django.shortcuts import render
from django.views import View
from subekashi.models import Song
from subekashi.lib.song_service import get_song_links_with_media
import re


class SongView(View):
    def get(self, request, song_id):
        song = Song.get_or_none(song_id)
        if song is None:
            return render(request, 'subekashi/404.html', status=404)

        # URLのリンクを取得
        links = get_song_links_with_media(song)

        # 改行の設定
        br_lyrics = request.COOKIES.get("brlyrics", "normal")
        if br_lyrics == "normal":
            br_cleaned_lyrics = song.lyrics
        elif br_lyrics == "pack":
            br_cleaned_lyrics = re.sub(r"\n+", "\n", song.lyrics)
        elif br_lyrics == "brless":
            br_cleaned_lyrics = song.lyrics.replace("\n", "")

        # 模倣元songリストを取得
        imitate_list = song.imitates.all()

        # 模倣songリストを取得
        imitated_list = song.imitateds.all()

        # 模倣元曲数と模倣曲数の数をdescriptionに記述
        description = ""
        imitate_count = imitate_list.count()
        imitated_count = imitated_list.count()
        description += f"模倣元の数：{imitate_count}, " if imitate_count else ""
        description += f"模倣曲の数：{imitated_count}, " if imitated_count else ""

        # 歌詞の一部をdescriptionに記述
        description_lyrics = song.lyrics[:50]
        description += f"歌詞: {description_lyrics}" if description_lyrics else ""

        # 未完成かどうか
        is_lack = Song.is_lack(song_id)

        # タグを持っているかどうかの確認
        has_tag = any([
            is_lack, song.is_draft, song.is_original, song.is_joke, song.is_inst, song.is_deleted, song.is_limited,
            not song.is_subeana
        ])

        context = {
            "description": description,
            "metatitle": f"{song.title} / {song.authors_str()}",
            "song": song,
            "br_cleaned_lyrics": br_cleaned_lyrics,
            "authors": song.authors.all(),
            "is_lack": is_lack,
            "links": links,
            "imitate_list": imitate_list,
            "imitated_list": imitated_list,
            "has_tag": has_tag
        }
        return render(request, "subekashi/song.html", context)
