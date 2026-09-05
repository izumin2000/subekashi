"""
DBの照合順序（collation）に依存しないicontains/iexactの実装

MySQL移行(#593)でDB全体の照合順序をutf8mb4_bin（バイト完全一致）にしたため、
DjangoのMySQLバックエンドが照合順序に依存する単純なLIKE/=として実装している
icontains/iexactが、意図せず大文字小文字を区別するようになってしまった（#1092）。

一方、exact/contains/=はSQLite本来の挙動（バイト完全一致）に合わせて照合順序に
依存させたいため変更しない。UPPER()関数で両辺を明示的に大文字化することで、
icontains/iexactだけを照合順序に依存しない大文字小文字非依存の検索にする。
"""
from django.db.models import CharField, TextField
from django.db.models.lookups import IContains, IExact


class CaseFoldedIExact(IExact):
    def process_lhs(self, compiler, connection):
        lhs_sql, params = super().process_lhs(compiler, connection)
        return f"UPPER({lhs_sql})", params

    def process_rhs(self, compiler, connection):
        rhs_sql, params = super().process_rhs(compiler, connection)
        return f"UPPER({rhs_sql})", params


class CaseFoldedIContains(IContains):
    def process_lhs(self, compiler, connection):
        lhs_sql, params = super().process_lhs(compiler, connection)
        return f"UPPER({lhs_sql})", params

    def process_rhs(self, compiler, connection):
        rhs_sql, params = super().process_rhs(compiler, connection)
        return f"UPPER({rhs_sql})", params


def register():
    for field_class in (CharField, TextField):
        field_class.register_lookup(CaseFoldedIExact)
        field_class.register_lookup(CaseFoldedIContains)
