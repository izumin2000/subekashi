from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from subekashi.lib.url import get_all_media
from subekashi.lib.discord import send_discord
from subekashi.constants.constants import SONG_CARD_SP_MAX_FLAG_ICONS, SUBEANA_AUTHOR_ID
from config.settings import *


register = template.Library()

# 全てあなたの所為です。の曲（合作を含む）か。検索ではauthorsをprefetchしているため、filterではなくall()から探す
@register.filter
def is_subeana_author(song):
    return any(author.id == SUBEANA_AUTHOR_ID for author in song.authors.all())


@register.simple_tag
def get_author(song):
    authors = song.authors.all()

    # 合作の場合
    if authors.count() >= 2:
        return mark_safe(f'<i class="fas fa-user-friends"></i>合作')
    
    # 作者不明なら
    author = authors.first()
    if author is None:
        send_discord(ERROR_DISCORD_URL, f"作者が不明です： {ROOT_URL}/songs/{song.id}")
        return mark_safe('<i class="fas fa-user"></i>作者不明')
    
    # html特殊文字をエスケープ(一応)
    author_name = author.name.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    author_url = reverse('subekashi:author', kwargs={'author_id': author.id})
    return mark_safe(f'<object><a href="{author_url}"><i class="fas fa-user"></i>{author_name}</a></object>')


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

# PC幅で歌詞の欄に「インスト曲」と表示される曲か（スマホ幅では歌詞の欄を隠す）
def is_inst_in_lyrics(song):
    return song.is_inst and not song.lyrics and not song.is_questionable


# PC幅・スマホ幅の片方だけで表示するときのクラス
def get_display_class(is_pc, is_sp):
    if is_pc and not is_sp:
        return " song-card-pc-only"
    if is_sp and not is_pc:
        return " song-card-sp-only"
    return ""


# 曲ページのタグと同じ順・同じアイコン（未完成は曲カードには出さない）
def get_flag_icons(song, has_link):
    flags = song.get_flags()
    if not flags:
        return ""

    # PC幅では、歌詞の欄の「インスト曲」と重なるため、インスト曲のアイコンを出さない
    pc_flags = [flag for flag in flags if not (flag["name"] == "is_inst" and is_inst_in_lyrics(song))]
    # スマホ幅では、アイコンが多いときは三点リーダーにまとめる
    sp_flags = flags if len(flags) <= SONG_CARD_SP_MAX_FLAG_ICONS else flags[:SONG_CARD_SP_MAX_FLAG_ICONS - 1]

    tags = ""
    for flag in flags:
        is_pc = flag in pc_flags
        is_sp = flag in sp_flags
        if is_pc or is_sp:
            tags += f'<i class="{flag["icon"]}{get_display_class(is_pc, is_sp)}" title="{flag["label"]}"></i>'

    folded_flags = flags[len(sp_flags):]
    if folded_flags:
        folded_labels = "・".join(flag["label"] for flag in folded_flags)
        tags += f'<i class="fas fa-ellipsis-h song-card-sp-only" title="{folded_labels}"></i>'

    # リンクとの間を縦線で区切る
    if has_link:
        tags += f'<span class="song-card-separator{get_display_class(bool(pc_flags), True)}"></span>'
    return tags


@register.simple_tag
def get_url(song):
    active_links = song.links.all()
    link_tags = ""

    # 非公開でなく、URLが未登録なら
    if not song.is_deleted and not active_links.exists():
        edit_url = reverse('subekashi:song_edit', args=[song.id])
        link_tags = f'<a href="{edit_url}">URL未登録</a>'

    # URLを登録しているのなら
    for link in active_links:
        icon = get_all_media(link.url)["icon"]
        link_tags += f'<a href="{link.url}" target="_blank">{icon}</a>'

    flag_tags = get_flag_icons(song, bool(link_tags))
    return mark_safe(f'<object>{flag_tags}{link_tags}</object>')
        

@register.simple_tag
def get_lyrics(song):
    lyrics = song.lyrics[:50]
    # html特殊文字をエスケープ
    lyrics=lyrics.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    # インスト曲なら
    if not lyrics and song.is_inst:
        return mark_safe('<i class="fas fa-align-center"></i>インスト曲')

    # 未完成の判定（filter_by_lack）と同じく、歌詞の登録が必要なのは界隈曲?ではなく、カテゴリが曲の場合のみ（#1253）
    if not lyrics and (song.is_questionable or song.category != "song"):
        return ""

    # 歌詞を登録していないのなら
    if not lyrics and not song.is_inst:
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