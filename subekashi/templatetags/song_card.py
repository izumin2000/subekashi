from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from subekashi.lib.url import get_all_media


register = template.Library()

@register.simple_tag
def get_channel(song):
    # authorsフィールドから作者を取得
    authors_list = list(song.authors.all())
    author_names = [author.name for author in authors_list]

    # 合作なら
    if len(author_names) >= 2:
        return mark_safe('<i class="fas fa-user-friends"></i>合作')
    # 単作なら
    if not author_names:
        return mark_safe('<i class="fas fa-user-circle"></i>作者不明')
    author_name = author_names[0]
    # html特殊文字をエスケープ(一応)
    author_name = author_name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    author_url = reverse('subekashi:channel', args=[author_name])
    return mark_safe(f'<object><a href="{author_url}"><i class="fas fa-user-circle"></i>{author_name}</a></object>')


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
        edit_url = reverse('subekashi:song_edit', args=[song.id])
        return mark_safe(f'<object><a href="{edit_url}">URL未登録</a></object>')
    
    # URLを登録しているのなら
    for url in urls:
        icon = get_all_media(url)["icon"]
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
        edit_url = reverse('subekashi:song_edit', args=[song.id])
        return mark_safe(f'<object><a href="{edit_url}"><i class="fas fa-align-center"></i>歌詞未登録</a></object>')
    
    # 歌詞を登録しているのなら
    return mark_safe(f'<i class="fas fa-align-center"></i>{lyrics}')


@register.simple_tag
def render_song_card(song):
    context = {
        'song': song,
    }
    return render_to_string('subekashi/components/song_card.html', context)