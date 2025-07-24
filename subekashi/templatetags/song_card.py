from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from config.local_settings import ERROR_DISCORD_URL
from config.settings import ROOT_URL
from subekashi.lib.discord import *
from subekashi.lib.url import get_allow_media


register = template.Library()

@register.simple_tag
def get_channel(song):
    channels = song.channel.split(',')
    # 合作なら
    if len(channels) >= 2:
        return mark_safe('<i class="fas fa-user-friends"></i>合作')
    # 単作なら
    channel = channels[0]
    # html特殊文字をエスケープ(一応)
    channel = channel.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
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

@register.simple_tag
def get_url(song):
    urls = song.url.split(',') if song.url else ""
    i_tags = ""
    
    # 非公開なら
    if song.isdeleted:
        i_tags += "<i class='far fa-eye-slash'></i>"
    
    # 未登録なら
    elif not urls:
        new_url = reverse('subekashi:song_new')
        return mark_safe(f'<object><a href="{new_url}?id={song.id}">URL未登録</a></object>')
    
    # URLを登録しているのなら
    for url in urls:
        allow_url = get_allow_media(url)
        
        if allow_url:
            icon = allow_url["icon"]
        else :
            send_discord(ERROR_DISCORD_URL, f"{ROOT_URL}/songs/{song.id}\n想定外のURLが添付されました：{url}")
            icon = "<i class='fas fa-exclamation-circle'></i>"
        
        i_tags += f'<a href="{url}" target="_blank">{icon}</a>'
        
    return mark_safe(f'<object>{i_tags}</object>')
        

@register.simple_tag
def get_lyrics(song):
    lyrics = song.lyrics[:50]
    # html特殊文字をエスケープ
    lyrics=lyrics.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    # インスト曲なら
    if not lyrics and song.isinst:
        return mark_safe('<i class="fas fa-align-center"></i>インスト曲')
    
    # 歌詞を登録していないのなら
    if not lyrics and not song.isinst:
        new_url = reverse('subekashi:song_new')
        return mark_safe(f'<object><a href="{new_url}?id={song.id}"><i class="fas fa-align-center"></i>歌詞未登録</a></object>')
    
    # 歌詞を登録しているのなら
    return mark_safe(f'<i class="fas fa-align-center"></i>{lyrics}')


@register.simple_tag
def render_song_card(song):
    context = {
        'song': song,
    }
    return render_to_string('subekashi/components/song_card.html', context)