from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from subekashi.lib.discord import *
from urllib.parse import urlparse
import re


register = template.Library()

@register.simple_tag
def get_channel(song):
    channels = song.channel.replace(", ", ",").split(',')
    # 合作なら
    if len(channels) >= 2:
        return mark_safe('<i class="fas fa-user-friends"></i>合作')
    # 単作なら
    channel = channels[0]
    channel_url = reverse('subekashi:channel', args=[channel])
    return mark_safe(f'<object><a href="{channel_url}"><i class="fas fa-user-circle"></i>{channel}</a></object>')


@register.simple_tag
def get_like(song):
    like = song.like
    if not like:
        return ""
    
    return mark_safe(f'<i class="far fa-thumbs-up"></i>{like}')


@register.simple_tag
def get_view(song):
    view = song.view
    if not view:
        return ""
    
    return mark_safe(f'<i class="fas fa-play"></i>{view}')


# TODO 定数化
DEFALT_ICON = "<i class='fas fa-globe'></i>"
URL_ICON = {
    r"(?:^|\.)youtu\.be$": "<i class='fab fa-youtube'></i>",
    r"(?:^|\.)youtube\.com$": "<i class='fab fa-youtube'></i>",
    r"(?:^|\.)soundcloud\.com$": "<i class='fab fa-soundcloud'></i>",
    r"(?:^|\.)x\.com$": "<i class='fab fa-twitter'></i>",
    r"(?:^|\.)twitter.com$": "<i class='fab fa-twitter'></i>",
    r"(?:^|\.)bandcamp.com$": "<i class='fab fa-bandcamp'></i>",
    r"drive\.google\.com": "<i class='fab fa-google-drive'></i>",
    r"(?:^|\.)nicovideo\.jp$": f"<img src='/static/subekashi/image/niconico.png' alt='ニコニコ動画'></img>",
    r"(?:^|\.)bilibili\.com$": f"<img src='/static/subekashi/image/bilibili.png' alt='ビリビリ動画'></img>",
    r"imicomweb\.com": f"<img src='/static/subekashi/image/imicomweb.png' alt='イミコミュ'></img>",
    r"scratch\.mit\.edu": DEFALT_ICON,
}

@register.simple_tag
def get_url(song):
    urls = song.url.replace(", ", ",").split(',') if song.url else ""
    i_tags = ""
    
    # 非公開なら
    if song.isdeleted:
        i_tags += "<i class='far fa-eye-slash'></i>"
    
    # 未登録なら
    elif not urls:
        new_url = reverse('subekashi:new')
        return mark_safe(f'<object><a href="{new_url}?id={song.id}">URL未登録</a></object>')
    
    # URLを登録しているのなら
    for url in urls:
        domain = urlparse(url).netloc
        pattern_list = [bool(re.search(allow_pattern, domain)) for allow_pattern in URL_ICON.keys()]
        if any(pattern_list):
            icon = list(URL_ICON.values())[pattern_list.index(True)]
        else :
            sendDiscord(ERROR_DISCORD_URL, f"{ROOT_URL}/songs/{song.id}\n想定外のURLが添付されました：{url}")
            icon = "<i class='fas fa-exclamation-circle'></i>"
        i_tags += f'<a href="{url}" target="_blank">{icon}</a>'
        
    return mark_safe(f'<object>{i_tags}</object>')
        

@register.simple_tag
def get_lyrics(song):
    lyrics = song.lyrics
    
    # インスト曲なら
    if not lyrics and song.isinst:
        return mark_safe('<i class="fas fa-align-center"></i>インスト曲')
    
    # 歌詞を登録していないのなら
    if not lyrics and not song.isinst:
        new_url = reverse('subekashi:new')
        return mark_safe(f'<object><a href="{new_url}?id={song.id}"><i class="fas fa-align-center"></i>歌詞未登録</a></object>')
    
    # 歌詞を登録しているのなら
    return mark_safe(f'<i class="fas fa-align-center"></i>{lyrics}')


@register.simple_tag
def render_song_card(song):
    context = {
        'song': song,
    }
    return render_to_string('subekashi/components/song_card.html', context)