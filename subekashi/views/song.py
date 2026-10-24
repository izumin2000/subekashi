from django.shortcuts import render
from django.views import View
from subekashi.models import Song
from subekashi.lib.song_service import get_song_links_with_media, get_short_and_full_songs, split_songs_by_category
from subekashi.views.song_removed import render_song_not_found
import re


class SongView(View):
    def get(self, request, song_id):
        song = Song.get_or_none(song_id)
        if song is None:
            return render_song_not_found(request, song_id)

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

        # タイトルと名義から判断したfull版・short版のリストを取得
        full_songs, short_songs = get_short_and_full_songs(song)

        # 模倣元曲数と模倣曲数の数をdescriptionに記述
        description = ""
        imitate_count = imitate_list.count()
        imitated_count = imitated_list.count()
        description += f"模倣元の数：{imitate_count}, " if imitate_count else ""
        description += f"模倣曲の数：{imitated_count}, " if imitated_count else ""

        # 歌詞の一部をdescriptionに記述
        description_lyrics = song.lyrics[:50]
        description += f"歌詞: {description_lyrics}" if description_lyrics else ""

        # タグに表示するフラグ
        flags = song.get_flags(is_lack=Song.is_lack(song_id))

        # タグに表示するカテゴリ（カテゴリが曲の場合は表示しない）
        category = song.get_category() if song.category != "song" else None

        context = {
            "description": description,
            "metatitle": f"{song.title} / {song.authors_str()}",
            "song": song,
            "br_cleaned_lyrics": br_cleaned_lyrics,
            "authors": song.authors.all(),
            "links": links,
            "imitate_list": imitate_list,
            "imitated_list": imitated_list,
            # 模倣元・模倣曲のうち、ネタ曲と曲以外のカテゴリの曲はdetailsにまとめる
            "imitate_groups": split_songs_by_category(imitate_list),
            "imitated_groups": split_songs_by_category(imitated_list),
            "full_songs": full_songs,
            "short_songs": short_songs,
            "flags": flags,
            "category": category,
        }
        return render(request, "subekashi/song.html", context)
