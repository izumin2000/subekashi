"""
Author関連のヘルパー関数
"""
from subekashi.models import Author, AuthorAlias


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
    author_objects = []
    for name in author_names:
        if not name:  # 空文字列をスキップ
            continue
        past_alias = AuthorAlias.objects.filter(name=name, alias_type="past").select_related("author").first()
        if past_alias is not None:
            author_objects.append(past_alias.author)
            continue
        author, _ = Author.objects.get_or_create(name=name)
        author_objects.append(author)
    return author_objects
