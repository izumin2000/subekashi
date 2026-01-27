from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.filter import is_lack
from subekashi.lib.url import get_all_media
import re


def song(request, song_id):
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    # URLのリンクを取得
    links = []
    for url in song.url.split(",") if song.url else []:
        media = get_all_media(url)
        links.append(
            {
                "text": url,
                "icon": media["icon"],
                "name": media["name"]
            }
        )
    
    # 改行の設定
    br_lyrics = request.COOKIES.get("brlyrics", "normal")
    if br_lyrics == "normal":
        br_cleaned_lyrics = song.lyrics
    elif br_lyrics == "pack":
        br_cleaned_lyrics = re.sub(r"\n+", "\n", song.lyrics)
    elif br_lyrics == "brless":
        br_cleaned_lyrics = song.lyrics.replace("\n", "")
        
    # 模倣元songリストを取得
    imitate_list = Song.objects.none()
    for imitate_id in song.imitate.split(",") if song.imitate else []:
        imitate_or_none = Song.objects.filter(id = imitate_id)
        imitate_list |= imitate_or_none
    
    # 模倣songリストを取得
    imitated_list = Song.objects.none()
    for imitated_id in song.imitated.split(",") if song.imitated else []:
        imitated_or_none = Song.objects.filter(id = imitated_id)
        imitated_list |= imitated_or_none

    # 模倣元曲数と模倣曲数の数をdescriptionに記述
    # TODO countじゃなくてexist
    description = ""
    description += f"模倣元の数：{imitate_list.count()}, " if imitate_list.count() else ""
    description += f"模倣曲の数：{imitated_list.count()}, " if imitated_list.count() else ""

    # 歌詞の一部をdescriptionに記述
    description_lyrics = song.lyrics[:50]
    description += f"歌詞: {description_lyrics}" if description_lyrics else ""
    
    # タグを持っているかどうかの確認
    has_tag = False
    has_tag |= song.authors.filter(id=1).exists()
    has_tag |= is_lack(song) or song.isdraft or song.isoriginal or song.isjoke or song.isinst
    has_tag |= not(song.issubeana) or song.isdeleted
    
    # テンプレートに渡す辞書を作成
    dataD = {
        "description": description,
        "metatitle": f"{song.title} / {song.authors_str()}",
        "song": song,
        "br_cleaned_lyrics": br_cleaned_lyrics,
        "authors": song.authors.all(),
        "is_lack": is_lack(song),
        "links": links,
        "imitate_list": imitate_list,
        "imitated_list": imitated_list,
        "has_tag": has_tag
    }
    return render(request, "subekashi/song.html", dataD)