import re
from urllib.parse import quote, urlparse
from subekashi.lib.url import is_youtube_url, get_youtube_id, format_bilibili_url

# 曲ページの埋め込みプレイヤー（#1254）
# 公式がiframeでの埋め込みに対応していて、URLから埋め込み用のURLを作れるサービスのみ対象にする
# shape: iframeの形（video: 16:9、audio: 横長のプレイヤー、playlist: 曲の一覧付きのプレイヤー、scratch: Scratchの作品）

_NICOVIDEO_RE = re.compile(r'https?://(?:www\.|sp\.)?nicovideo\.jp/watch/((?:sm|nm|so)?[0-9]+)(?:[/?#]|$)')
_BILIBILI_RE = re.compile(r'https://bilibili\.com/video/(BV1[0-9A-Za-z]{9})(?:\?p=([0-9]+))?$')
_GOOGLE_DRIVE_RE = re.compile(r'https?://drive\.google\.com/file/(?:u/[0-9]+/)?d/([A-Za-z0-9_-]+)')
_SCRATCH_RE = re.compile(r'https?://scratch\.mit\.edu/projects/([0-9]+)')

_YOUTUBE_HOSTS = ('youtu.be', 'youtube.com', 'www.youtube.com', 'm.youtube.com')
_SOUNDCLOUD_HOSTS = ('soundcloud.com', 'www.soundcloud.com', 'm.soundcloud.com')
# 曲ではなく、ユーザーのページの中のタブ
_SOUNDCLOUD_PROFILE_TABS = {'tracks', 'albums', 'sets', 'reposts', 'likes', 'popular-tracks', 'followers', 'following', 'comments'}


def _embed_youtube(url):
    if urlparse(url).netloc not in _YOUTUBE_HOSTS or not is_youtube_url(url):
        return None
    return {"src": f"https://www.youtube-nocookie.com/embed/{get_youtube_id(url)}", "shape": "video"}


def _embed_nicovideo(url):
    match = _NICOVIDEO_RE.match(url)
    if not match:
        return None
    return {"src": f"https://embed.nicovideo.jp/watch/{match.group(1)}", "shape": "video"}


# 「soundcloud.com/<ユーザー>/<曲>」と「soundcloud.com/<ユーザー>/sets/<プレイリスト>」が対象。ユーザーのページは対象外
def _embed_soundcloud(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc not in _SOUNDCLOUD_HOSTS:
        return None

    segments = [segment for segment in parsed_url.path.split('/') if segment]
    if len(segments) == 2 and segments[1] not in _SOUNDCLOUD_PROFILE_TABS:
        shape = "audio"
    elif len(segments) == 3 and segments[1] == 'sets':
        shape = "playlist"
    else:
        return None

    page_url = f"https://soundcloud.com/{'/'.join(segments)}"
    return {"src": f"https://w.soundcloud.com/player/?url={quote(page_url, safe='')}&visual=false", "shape": shape}


# format_bilibili_urlでav番号をBV番号に揃えてから、BV番号と、2パート目以降の「?p=<n>」を取り出す
def _embed_bilibili(url):
    match = _BILIBILI_RE.match(format_bilibili_url(url))
    if not match:
        return None
    page = match.group(2) or '1'
    return {"src": f"https://player.bilibili.com/player.html?isOutside=true&bvid={match.group(1)}&p={page}&autoplay=0", "shape": "video"}


def _embed_google_drive(url):
    match = _GOOGLE_DRIVE_RE.match(url)
    if not match:
        return None
    return {"src": f"https://drive.google.com/file/d/{match.group(1)}/preview", "shape": "video"}


def _embed_scratch(url):
    match = _SCRATCH_RE.match(url)
    if not match:
        return None
    return {"src": f"https://scratch.mit.edu/projects/{match.group(1)}/embed", "shape": "scratch"}


_EMBEDDERS = (_embed_youtube, _embed_nicovideo, _embed_soundcloud, _embed_bilibili, _embed_google_drive, _embed_scratch)


# URLの埋め込み用のURLとiframeの形を返す。埋め込めないURLならNoneを返す
def get_embed(url):
    for embedder in _EMBEDDERS:
        embed = embedder(url)
        if embed:
            return embed
    return None
