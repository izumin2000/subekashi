"""
Author関連のヘルパー関数
"""
from subekashi.models import Author


def get_or_create_authors(author_names):
    """
    作者名のリストからAuthorオブジェクトのリストを返す

    Args:
        author_names: 作者名のリスト（空文字列を含む可能性あり）

    Returns:
        list[Author]: Authorオブジェクトのリスト
    """
    author_objects = []
    for name in author_names:
        if name:  # 空文字列をスキップ
            author, _ = Author.objects.get_or_create(name=name)
            author_objects.append(author)
    return author_objects
