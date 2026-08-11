from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from subekashi.constants.constants import ALL_MEDIAS
from subekashi.lib.url import clean_url
from subekashi.models import Author, AuthorAlias, SongLink

# alias_type="another"（別名義）は同一人物が運用していても意図的に区別して扱うべきものであり、
# 検索時に自動的に同一視されると意図しない結果になるため双方向解決の対象外とする（#996）
NON_ANOTHER_ALIAS_TYPES = [value for value, _ in AuthorAlias.CHOICES if value != "another"]

# authorの別名（双方向）にマッチするQを返す
# 正方向: authorに登録された別名がvalueにマッチする
# 逆方向: nameがauthor.nameと一致する別名を他のauthorが持ち、その別名がvalueにマッチする場合、
#         name側のauthorも対象にする（#989の双方向解決に対応）
def filter_by_author_alias(lookup, value):
    # name一致とalias_type制限を同一dictにまとめることで、複数aliasを持つauthorに対しても
    # 同一のAuthorAlias行に対して両条件が適用されるようにする
    # （否定条件(~Q)をANDすると多対多の行スコープが崩れるため、alias_type__inの正方向条件を使う）
    forward_condition = Q(**{
        f"authors__aliases__name__{lookup}": value,
        "authors__aliases__alias_type__in": NON_ANOTHER_ALIAS_TYPES,
    })
    reverse_names = (
        AuthorAlias.objects.exclude(alias_type="another")
        .filter(**{f"author__name__{lookup}": value})
        .values("name")
    )
    return forward_condition | Q(authors__name__in=reverse_names)

# 作者名によるフィルター（別名・双方向を含む、部分一致）
def filter_by_author(value):
    return Q(authors__name__icontains=value) | filter_by_author_alias("icontains", value)

# 作者名によるフィルター（別名・双方向を含む、完全一致）
def filter_by_author_exact(value):
    return Q(authors__name__exact=value) | filter_by_author_alias("exact", value)

# topやsearchにあるキーワード検索のフィルター
def filter_by_keyword(keyword):
    url_keyword = clean_url(keyword)
    return (
        Q(title__contains=keyword) |
        Q(authors__name__contains=keyword) |
        filter_by_author_alias("contains", keyword) |
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
        Q(authors__name__contains = guesser) |
        filter_by_author_alias("contains", guesser)
    )

# メディアの検索に利用するフィルター
def filter_by_mediatypes(mediatypes):
    # mediatypeに当てはまる正規表現を抜き出す
    # "other"（URL未登録）はリンクが1件も存在しないことを示すため、
    # links__url__regex では判定できず個別にExistsで判定する
    media_regex_list = []
    query = Q()
    for mediatype in mediatypes.split(","):
        if mediatype == "other":
            # 非公開/削除済みの曲は対象外とする
            any_links = SongLink.objects.filter(songs=OuterRef('pk'))
            query |= Q(is_deleted=False) & ~Exists(any_links)
            continue
        for i, media in enumerate(ALL_MEDIAS):
            if mediatype == media["id"]:
                media_regex_list.append(f"({ALL_MEDIAS[i]['regex']})")
                continue
    if media_regex_list:
        media_regex = "|".join(media_regex_list)
        query |= Q(links__url__regex=media_regex)
    return query

# 未完成フィルター
def filter_by_lack():
    any_links = SongLink.objects.filter(songs=OuterRef('pk'))
    has_author_1 = Author.objects.filter(id=1, songs__id=OuterRef('pk'))
    return (
        (Q(is_deleted=False) & ~Exists(any_links)) |
        (Q(is_questionable=False, is_original=False, is_subeana=True, imitates__isnull=True) & ~Exists(has_author_1)) |
        Q(is_questionable=False, is_inst=False, lyrics="")
    )


# is_lackアノテーション用のCase式を返す（Prefetch + annotateでN+1を回避する用途）
def make_is_lack_annotation():
    any_links = SongLink.objects.filter(songs=OuterRef('pk'))
    has_author_1 = Author.objects.filter(id=1, songs__id=OuterRef('pk'))
    return Case(
        When(Q(is_deleted=False) & ~Exists(any_links), then=Value(True)),
        When(Q(is_questionable=False, is_original=False, is_subeana=True, imitates__isnull=True) & ~Exists(has_author_1), then=Value(True)),
        When(Q(is_questionable=False, is_inst=False, lyrics=''), then=Value(True)),
        default=Value(False),
        output_field=BooleanField(),
    )
