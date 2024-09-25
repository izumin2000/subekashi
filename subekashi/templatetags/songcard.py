from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from subekashi.lib.discord import *
from urllib.parse import urlparse


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

DEFALT_ICON = "fas fa-globe"
URL_ICON = {
    "youtu.be": "fab fa-youtube",
    "youtube.com": "fab fa-youtube",
    "soundcloud.com": "fab fa-soundcloud",
    "x.com": "fab fa-twitter",
    "twitter.com": "fab fa-twitter",
    "bandcamp.com": "fab fa-bandcamp",
    "bilibili.com": DEFALT_ICON,
    "scratch.mit.edu": DEFALT_ICON,
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
        domain = urlparse(url).netloc.replace("www.", "")
        if not any(allow == domain for allow in URL_ICON.keys()):
            sendDiscord(ERROR_DISCORD_URL, f"想定外のURLが添付されました：{url}")
            
        icon = URL_ICON.get(domain, DEFALT_ICON)
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