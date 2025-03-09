from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.filter import is_lack
from subekashi.constants.constants import DEFALT_ICON, URL_ICON
from urllib.parse import urlparse
import re

def song(request, song_id):
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    # URLのリンクを取得
    links = []
    for url in song.url.split(",") if song.url else []:
        domain = urlparse(url).netloc
        pattern_list = [bool(re.search(allow_pattern, domain)) for allow_pattern in URL_ICON.keys()]
        icon = list(URL_ICON.values())[pattern_list.index(True)]
        links.append(
            {
                "text": url,
                "icon": icon
            }
        )
    
    # 模倣songリストを取得
    imitate_list = Song.objects.none()
    for imitate_id in song.imitate.split(",") if song.imitate else []:
        imitate_or_none = Song.objects.filter(id = imitate_id)
        imitate_list |= imitate_or_none
    
    # 被模倣songリストを取得
    imitated_list = Song.objects.none()
    for imitated_id in song.imitated.split(",") if song.imitated else []:
        imitated_or_none = Song.objects.filter(id = imitated_id)
        imitated_list |= imitated_or_none

    # 模倣曲数と被模倣曲数の数をdescriptionに記述
    description = ""
    description += f"模倣曲数：{imitate_list.count()}, " if imitate_list.count() else ""
    description += f"被模倣曲数：{imitated_list.count()}, " if imitated_list.count() else ""
    
    # 歌詞のHTML化
    br_lyrics = request.COOKIES.get("brlyrics", "normal")
    if br_lyrics == "normal":
        html_lyrics = song.lyrics.replace("\n", "<br>")
    elif br_lyrics == "pack":
        html_lyrics = re.sub(r"\n+", "<br>", song.lyrics)
    elif br_lyrics == "brless":
        html_lyrics = song.lyrics.replace("\n", "")
    
    # 歌詞の一部をdescriptionに記述
    description_lyrics = song.lyrics.replace("\r\n", "")[:100]
    description += f"歌詞: {description_lyrics}" if description_lyrics else ""
    
    # タグを持っているかどうかの確認
    has_tag = False
    has_tag |= song.channel == "全てあなたの所為です。"
    has_tag |= is_lack(song) or song.isdraft or song.isoriginal or song.isjoke or song.isinst
    has_tag |= not(song.issubeana) or song.isdeleted
    
    # テンプレートに渡す辞書を作成
    dataD = {
        "description": description,
        "metatitle": f"{song.title} / {song.channel}",
        "song": song,
        "channels": song.channel.split(","),
        "is_lack": is_lack(song),
        "links": links,
        "imitate_list": imitate_list,
        "imitated_list": imitated_list,
        "has_tag": has_tag,
        "lyrics": html_lyrics
    }
    return render(request, "subekashi/song.html", dataD)