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
    if like == 0:
        return ""
    
    return mark_safe(f'<i class="far fa-thumbs-up"></i>{like}')


@register.simple_tag
def get_view(song):
    view = song.view
    if view == 0:
        return ""
    
    return mark_safe(f'<i class="fas fa-play"></i>{view}')


# TODO 定数化
DEFALT_ICON = "fas fa-globe"
URL_ICON = {
    r"(?:^|\.)youtu\.be$": "fab fa-youtube",
    r"(?:^|\.)youtube\.com$": "fab fa-youtube",
    r"(?:^|\.)soundcloud\.com$": "fab fa-soundcloud",
    r"(?:^|\.)x\.com$": "fab fa-twitter",
    r"(?:^|\.)twitter.com$": "fab fa-twitter",
    r"(?:^|\.)bandcamp.com$": "fab fa-bandcamp",
    r"drive\.google\.com": "fab fa-google-drive",
    r"(?:^|\.)nicovideo\.jp$": DEFALT_ICON,        # TODO アイコンを追加する
    r"(?:^|\.)bilibili\.com$": DEFALT_ICON,
    r"scratch\.mit\.edu": DEFALT_ICON,
    r"imicomweb\.com": DEFALT_ICON,
}

@register.simple_tag
def get_url(song):
    urls = song.url.replace(", ", ",").split(',') if song.url else ""
    
    # 非公開なら
    if not urls and song.isdeleted:
        return '非公開/削除済み'
    
    # 未登録なら
    if not urls and not song.isdeleted:
        new_url = reverse('subekashi:new')
        return mark_safe(f'<object><a href="{new_url}?id={song.id}">URL未登録</a></object>')
    
    # URLを登録しているのなら
    i_tags = ""
    for url in urls:
        domain = urlparse(url).netloc
        pattern_list = [bool(re.search(allow_pattern, domain)) for allow_pattern in URL_ICON.keys()]
        if any(pattern_list):
            icon = list(URL_ICON.values())[pattern_list.index(True)]
        else :
            # sendDiscord(ERROR_DISCORD_URL, f"{ROOT_DIR}/songs/{song.id}\n想定外のURLが添付されました：{url}")
            print([re.search(allow_pattern, domain) for allow_pattern in URL_ICON.keys()])
            print(f'\033[31m{ROOT_DIR}/songs/{song.id}\n想定外のURLが添付されました：{url}\033[0m')
            icon = DEFALT_ICON
        i_tags += f'<a href="{url}" target="_blank"><i class="{icon}"></i></a>'
        
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
def render_songcard(song):
    context = {
        'song': song,
    }
    return render_to_string('subekashi/components/songcard.html', context)