from collections import deque
from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from subekashi.constants.constants import ALL_MEDIAS
from subekashi.lib.url import clean_url
from subekashi.models import Author, AuthorAlias, SongLink

# 中継点（推移的な探索での2ホップ目以降）として使える種別。
# alias_type="another"（別名義）は同一人物が運用していても意図的に区別して扱うべきものであり、
# 検索では正方向・逆方向とも一切考慮しない（#996、#1004で撤回した「除外撤回」を再度撤回）。
# alias_type="group"（グループ）はメンバー→グループの片方向のみ考慮する（#1006、詳細は#1003参照）。
BRIDGING_ALIAS_TYPES = [value for value, _ in AuthorAlias.CHOICES if value not in ("another", "group")]


def _bridging_cluster(seed_names):
    """seed_namesを起点に、BRIDGING_ALIAS_TYPESの関係のみを辿って到達できる
    Author名の集合を返す（#1005のAuthor.get_transitive_aliases()と同じ、
    another・groupを中継点にしないルールを名前の集合に対して適用したもの）。
    """
    visited = set(seed_names)
    queue = deque(seed_names)
    while queue:
        name = queue.popleft()
        author = Author.get_by_name(name)
        neighbor_names = set()
        if author is not None:
            neighbor_names |= set(
                author.aliases.filter(alias_type__in=BRIDGING_ALIAS_TYPES).values_list("name", flat=True)
            )
        neighbor_names |= set(
            AuthorAlias.objects.filter(name=name, alias_type__in=BRIDGING_ALIAS_TYPES)
            .exclude(author=author)
            .values_list("author__name", flat=True)
        )
        for neighbor_name in neighbor_names:
            if neighbor_name not in visited:
                visited.add(neighbor_name)
                queue.append(neighbor_name)
    return visited


def _resolve_author_alias_names(lookup, value):
    """検索語(value)に対応する実効的なAuthor名の集合を返す（#1006）

    - alias_type="another"は正方向・逆方向とも一切考慮しない
    - alias_type="group"はメンバー→グループの片方向のみ考慮する
      （グループ自身の名義で検索してもメンバー個々の曲は含めない）
    - それ以外の種別（id/abbr/common/past/sns/spell）は推移的に双方向解決する
    """
    forward_owner_names = set(
        AuthorAlias.objects.filter(**{f"name__{lookup}": value}, alias_type__in=BRIDGING_ALIAS_TYPES)
        .values_list("author__name", flat=True)
    )
    reverse_anchor_names = set(
        Author.objects.filter(**{f"name__{lookup}": value}).values_list("name", flat=True)
    )
    seed_names = forward_owner_names | reverse_anchor_names
    if not seed_names:
        return set()

    cluster_names = _bridging_cluster(seed_names)
    group_target_names = set(
        AuthorAlias.objects.filter(author__name__in=cluster_names, alias_type="group")
        .values_list("name", flat=True)
    )
    return cluster_names | group_target_names


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
