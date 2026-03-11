from django.db.models import Q
from subekashi.constants.constants import ALL_MEDIAS
from subekashi.lib.url import clean_url

# topやsearchにあるキーワード検索のフィルター
def filter_by_keyword(keyword):
    q = (
        Q(title__contains = keyword) |
        Q(authors__name__contains = keyword) |
        Q(lyrics__contains = keyword)
    )
    # URLっぽいキーワード（://を含む）の場合のみURLフィールドも検索
    url_keyword = clean_url(keyword)
    if '://' in url_keyword:
        q |= Q(url__contains = url_keyword)
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
        Q(url__regex = media_regex)
    )

# 未完成フィルター
filter_by_lack = (
    Q(isdeleted=False, url="") |
    Q(isoriginal=False, issubeana=True, imitate="") & ~Q(authors__id=1) |
    Q(isinst=False, lyrics="")
)