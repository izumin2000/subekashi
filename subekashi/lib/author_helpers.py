"""
Author関連のヘルパー関数
"""
from subekashi.models import Author, AuthorAlias


def _non_empty_names(author_names):
    return [name for name in author_names if name]  # 空文字列をスキップ


def validate_author_name_lengths(author_names):
    """作者名の長さを検証する。上限を超えるものがあればエラーメッセージを返す。問題なければNone。

    エラーメッセージにはユーザー入力の作者名がそのまま含まれるため、呼び出し側で
    HTMLエスケープしてから画面に表示すること（views/song_edit.pyのcontext["error"]は
    song_edit.html側で|safeによりオートエスケープが無効化されているため必須）。
    """
    max_length = Author._meta.get_field('name').max_length
    for name in _non_empty_names(author_names):
        if len(name) > max_length:
            # トースト表示が崩れないよう、メッセージに含める名前自体は短く切り詰める
            displayed_name = name if len(name) <= 50 else name[:50] + "…"
            return f"作者名は{max_length}文字以下である必要があります：{displayed_name}"
    return None


def get_or_create_authors(author_names):
    """
    作者名のリストからAuthorオブジェクトのリストを返す

    入力がalias_type="past"（以前の名称）のAuthorAlias.nameと完全一致する場合は、
    そのauthor（＝現在の一番有名な名義）に変換してから解決する（#996で見送られた
    正規化機能を、past種別に限定した形で復活させたもの、#1008）。
    それ以外の種別（another・group等）は意図的に区別して扱うべきものであり、
    自動的に同一視すると別人格として運用している名義まで巻き込んでしまうため対象外とする。

    Args:
        author_names: 作者名のリスト（空文字列を含む可能性あり）

    Returns:
        list[Author]: Authorオブジェクトのリスト
    """
    non_empty_names = _non_empty_names(author_names)

    # past別名の存在チェックを名前ごとに都度発行せず、1クエリで一括取得する
    past_authors_by_name = {
        alias.name: alias.author
        for alias in AuthorAlias.objects.filter(
            name__in=non_empty_names, alias_type="past"
        ).select_related("author")
    }

    author_objects = []
    for name in non_empty_names:
        past_author = past_authors_by_name.get(name)
        if past_author is not None:
            author_objects.append(past_author)
            continue
        author, _ = Author.objects.get_or_create(name=name)
        author_objects.append(author)
    return author_objects


def author_names_were_normalized(author_names, authors):
    """
    get_or_create_authors(author_names)の戻り値がauthorsであるとき、
    past別名から一番有名な名義への正規化が1件でも発生したかどうかを返す（#1029）

    Args:
        author_names: get_or_create_authors()に渡したものと同じ入力
        authors: get_or_create_authors(author_names)の戻り値

    Returns:
        bool
    """
    non_empty_names = _non_empty_names(author_names)
    return any(name != author.name for name, author in zip(non_empty_names, authors))
