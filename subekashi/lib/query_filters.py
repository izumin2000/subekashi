from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from subekashi.constants.constants import ALL_MEDIAS
from subekashi.lib.url import clean_url
from subekashi.models import Author, SongLink

# topやsearchにあるキーワード検索のフィルター
def filter_by_keyword(keyword):
    url_keyword = clean_url(keyword)
    return (
        Q(title__contains=keyword) |
        Q(authors__name__contains=keyword) |
        Q(lyrics__contains=keyword) |
        Q(links__url__icontains=url_keyword)
    )

# 模倣元のフィルター
def filter_by_imitate(imitate):
    return Q(imitates__id=imitate)

# 模倣のフィルター
def filter_by_imitated(imitated):
    return Q(imitateds__id=imitated)

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
        Q(is_deleted=False) & ~Exists(any_links) |
        Q(is_original=False, is_subeana=True, imitates__isnull=True) & ~Exists(has_author_1) |
        Q(is_inst=False, lyrics="")
    )


# is_lackアノテーション用のCase式を返す（Prefetch + annotateでN+1を回避する用途）
def make_is_lack_annotation():
    any_links = SongLink.objects.filter(songs=OuterRef('pk'))
    has_author_1 = Author.objects.filter(id=1, songs__id=OuterRef('pk'))
    return Case(
        When(Q(is_deleted=False) & ~Exists(any_links), then=Value(True)),
        When(Q(is_original=False, is_subeana=True, imitates__isnull=True) & ~Exists(has_author_1), then=Value(True)),
        When(Q(is_inst=False, lyrics=''), then=Value(True)),
        default=Value(False),
        output_field=BooleanField(),
    )
