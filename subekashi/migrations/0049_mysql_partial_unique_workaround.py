from django.db import migrations


# MySQLは条件付きUniqueConstraint（部分インデックス）をサポートしないため
# （models.W036、#593）、生成列（Generated/Virtual Column）による代替実装で
# 同等のDBレベル制約を再現する。
#
# 仕組み: 対象条件を満たす行だけ値を持ち、それ以外はNULLになる仮想列を追加し、
# その列に通常のユニークインデックスを張る。MySQLのユニークインデックスは
# 複数のNULLを許容するため、結果的に「条件付きユニーク制約」と同じ効果になる。
#
# SQLite・PostgreSQLでは元のUniqueConstraint(condition=...)がそのまま機能するため、
# MySQL以外では何もしない。生成列はDjangoのモデル定義には含めず、DB側にのみ
# 存在させる（makemigrations --checkの差分検知には影響しない）。
#
# author_idとの複合ユニークは、区切り文字としてNUL文字(CHAR(0))を挟んで
# nameとauthor_idを連結することで1列に落とし込んでいる（通常のname文字列には
# NUL文字が含まれないため、name末尾の数字とauthor_idの境界が曖昧になる心配がない）。

MYSQL_STATEMENTS = [
    (
        "ALTER TABLE subekashi_authoralias "
        "ADD COLUMN mysql_unique_name_except_group VARCHAR(500) "
        "GENERATED ALWAYS AS (CASE WHEN alias_type <> 'group' THEN name END) VIRTUAL",
        "ALTER TABLE subekashi_authoralias DROP COLUMN mysql_unique_name_except_group",
    ),
    (
        "ALTER TABLE subekashi_authoralias "
        "ADD UNIQUE INDEX mysql_uniq_name_except_group (mysql_unique_name_except_group)",
        "ALTER TABLE subekashi_authoralias DROP INDEX mysql_uniq_name_except_group",
    ),
    (
        # nameはmax_length=500、author_id(BigAutoField)は最大19桁+区切り文字1文字で
        # 理論上の最大長は520文字のため、余裕を持たせて521にする（コードレビュー対応）
        "ALTER TABLE subekashi_authoralias "
        "ADD COLUMN mysql_unique_name_author_for_group VARCHAR(521) "
        "GENERATED ALWAYS AS (CASE WHEN alias_type = 'group' "
        "THEN CONCAT(name, CHAR(0), author_id) END) VIRTUAL",
        "ALTER TABLE subekashi_authoralias DROP COLUMN mysql_unique_name_author_for_group",
    ),
    (
        "ALTER TABLE subekashi_authoralias "
        "ADD UNIQUE INDEX mysql_uniq_name_author_for_group (mysql_unique_name_author_for_group)",
        "ALTER TABLE subekashi_authoralias DROP INDEX mysql_uniq_name_author_for_group",
    ),
    (
        "ALTER TABLE subekashi_ai "
        "ADD COLUMN mysql_unique_janome_lyrics VARCHAR(100) "
        "GENERATED ALWAYS AS (CASE WHEN genetype = 'janome' THEN lyrics END) VIRTUAL",
        "ALTER TABLE subekashi_ai DROP COLUMN mysql_unique_janome_lyrics",
    ),
    (
        "ALTER TABLE subekashi_ai "
        "ADD UNIQUE INDEX mysql_uniq_janome_lyrics (mysql_unique_janome_lyrics)",
        "ALTER TABLE subekashi_ai DROP INDEX mysql_uniq_janome_lyrics",
    ),
]


def add_mysql_partial_unique_workaround(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    with schema_editor.connection.cursor() as cursor:
        for forward_sql, _reverse_sql in MYSQL_STATEMENTS:
            cursor.execute(forward_sql)


def remove_mysql_partial_unique_workaround(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    with schema_editor.connection.cursor() as cursor:
        for _forward_sql, reverse_sql in reversed(MYSQL_STATEMENTS):
            cursor.execute(reverse_sql)


class Migration(migrations.Migration):

    dependencies = [
        ("subekashi", "0001_squashed_0048_alter_author_name_alter_songlink_url"),
    ]

    operations = [
        migrations.RunPython(
            add_mysql_partial_unique_workaround,
            remove_mysql_partial_unique_workaround,
        ),
    ]
