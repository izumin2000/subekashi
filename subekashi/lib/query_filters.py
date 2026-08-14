from collections import deque
from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from subekashi.constants.constants import ALL_MEDIAS
from subekashi.lib.url import clean_url
from subekashi.models import Author, AuthorAlias, SongLink
from subekashi.models.author import NON_BRIDGING_ALIAS_TYPES, get_alias_edges


def _bridging_cluster(seed_names):
    """seed_namesを起点に、NON_BRIDGING_ALIAS_TYPES（another・group）以外の
    関係のみを辿って到達できるAuthor名の集合を返す。

    #1005のAuthor.get_transitive_aliases()と同じ非中継ルールを、特定のAuthorに
    紐付かない名前の集合に対して適用したもので、辺の取得自体はget_alias_edges()
    を共通利用することでget_transitive_aliases()とロジックの二重化を避けている。
    """
    visited = set(seed_names)
    queue = deque(seed_names)
    while queue:
        name = queue.popleft()
        author = Author.get_by_name(name)
        for target_name, alias_type, _source, _is_reverse in get_alias_edges(name, author):
            if alias_type in NON_BRIDGING_ALIAS_TYPES:
                continue
            if target_name not in visited:
                visited.add(target_name)
                queue.append(target_name)
    return visited


def _resolve_author_alias_names(lookup, value):
    """検索語(value)に対応する実効的なAuthor名の集合を返す（#1006）

    - alias_type="another"・"group"は正方向・逆方向とも一切考慮しない
      （グループ自身の名義・メンバー名義のどちらで検索しても、もう一方は含めない）
    - それ以外の種別（id/abbr/common/past/sns/spell）は推移的に双方向解決する
    """
    forward_owner_names = set(
        AuthorAlias.objects.filter(**{f"name__{lookup}": value})
        .exclude(alias_type__in=NON_BRIDGING_ALIAS_TYPES)
        .values_list("author__name", flat=True)
    )
    reverse_anchor_names = set(
        Author.objects.filter(**{f"name__{lookup}": value}).values_list("name", flat=True)
    )
    seed_names = forward_owner_names | reverse_anchor_names
    if not seed_names:
        return set()

    return _bridging_cluster(seed_names)


# authorの別名（推移的な双方向解決を含む）にマッチするQを返す（#1005/#1006）
def filter_by_author_alias(lookup, value):
    return Q(authors__name__in=_resolve_author_alias_names(lookup, value))

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
