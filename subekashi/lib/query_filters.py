from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from subekashi.constants.constants import ALL_MEDIAS
from subekashi.lib.url import clean_url
from subekashi.models import Author, SongLink

# topやsearchにあるキーワード検索のフィルター
def filter_by_keyword(keyword):
    q = (
        Q(title__contains = keyword) |
        Q(authors__name__contains = keyword) |
        Q(lyrics__contains = keyword)
    )
    # URLっぽいキーワード（://を含む）の場合のみSongLinkも検索
    url_keyword = clean_url(keyword)
    if '://' in url_keyword:
        q |= Q(links__url__icontains=url_keyword)
    return q

# 模倣元のフィルター
def filter_by_imitate(imitate):
    imitate = str(imitate)
    return (
        Q(imitate = imitate) |
        Q(imitate__startswith = imitate + ',') |
        Q(imitate__endswith = ',' + imitate) |
        Q(imitate__contains = ',' + imitate + ',')
    )

# 模倣のフィルター
def filter_by_imitated(imitated):
    imitated = str(imitated)
    return (
        Q(imitated = imitated) |
        Q(imitated__startswith = imitated + ',') |
        Q(imitated__endswith = ',' + imitated) |
        Q(imitated__contains = ',' + imitated + ',')
    )

# 模倣元の検索に利用するフィルター
def filter_by_guesser(guesser):
    return (
        Q(title__contains = guesser) |
        Q(authors__name__contains = guesser)
    )

# メディアの検索に利用するフィルター
def filter_by_mediatypes(mediatypes):
    # mediatypeに当てはまる正規表現を抜き出す
    media_regex_list = []
    for mediatype in mediatypes.split(","):
        for i, media in enumerate(ALL_MEDIAS):
            if mediatype == media["id"]:
                media_regex_list.append(f"({ALL_MEDIAS[i]['regex']})")
                continue
    media_regex = "|".join(media_regex_list)
    return (
        Q(links__url__regex=media_regex)
    )

# 未完成フィルター
def filter_by_lack():
    any_links = SongLink.objects.filter(songs=OuterRef('pk'))
    has_author_1 = Author.objects.filter(id=1, songs__id=OuterRef('pk'))
    return (
        Q(isdeleted=False) & ~Exists(any_links) |
        Q(isoriginal=False, issubeana=True, imitate="") & ~Exists(has_author_1) |
        Q(isinst=False, lyrics="")
    )


# is_lackアノテーション用のCase式を返す（Prefetch + annotateでN+1を回避する用途）
def make_is_lack_annotation():
    any_links = SongLink.objects.filter(songs=OuterRef('pk'))
    has_author_1 = Author.objects.filter(id=1, songs__id=OuterRef('pk'))
    return Case(
        When(Q(isdeleted=False) & ~Exists(any_links), then=Value(True)),
        When(Q(isoriginal=False, issubeana=True, imitate='') & ~Exists(has_author_1), then=Value(True)),
        When(Q(isinst=False, lyrics=''), then=Value(True)),
        default=Value(False),
        output_field=BooleanField(),
    )
