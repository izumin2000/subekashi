from collections import deque
from dataclasses import dataclass
from django.db import models
from .base import GetOrNoneMixin

# 中継点（2ホップ目以降の推移探索）として使わないalias_type（Author.get_transitive_aliases()参照）
NON_BRIDGING_ALIAS_TYPES = ("another", "group")


def get_alias_edges(name, author):
    """nameのノードから伸びるAuthorAliasの辺を全て返す（alias_typeによる絞り込みはしない）

    (target_name, alias_type, source, is_reverse) のタプルのリストを返す。
    正方向: authorが直接所有するAuthorAlias（authorがNone、つまりnameに対応する
    Authorが実在しない場合は正方向の辺は存在しない）
    逆方向: nameをname属性として持つ、他のauthorが所有するAuthorAlias

    AuthorAlias.authorはnull不可のフィールドのため、authorがNoneの場合の
    `.exclude(author=author)`（`.exclude(author=None)`）は何も除外しない
    no-opとして働き、意図通りに動作する。

    Author.get_transitive_aliases()（#1005）とsubekashi.lib.query_filtersの
    検索フィルター（#1006）で共通利用する低レベルヘルパー。
    """
    edges = []
    if author is not None:
        edges += [
            (alias.name, alias.alias_type, alias, False)
            for alias in author.aliases.all()
        ]
    edges += [
        (alias.author.name, alias.alias_type, alias, True)
        for alias in AuthorAlias.objects.filter(name=name).exclude(author=author).select_related("author")
    ]
    return edges


# 曲の作者の情報
class Author(GetOrNoneMixin, models.Model):
    name = models.CharField(unique=True, max_length = 255)

    def __str__(self):
        return self.name

    @classmethod
    def get_by_name(cls, name):
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            return None

    def get_effective_aliases(self):
        """双方向解決を含む実効的な別名一覧を返す

        正方向: 自身に登録されたAuthorAlias
        逆方向: nameが自身のname属性と一致する、他のauthorが持つAuthorAlias
        （そのauthorのnameを別名として扱う）

        呼び出しごとに2クエリ（正方向・逆方向）発行するため、複数authorに対して
        ループで呼び出すとN+1になる。一覧表示等で複数author分をまとめて扱う場合は
        呼び出し側でprefetch_relatedや一括取得を検討すること。
        """
        forward = [
            EffectiveAlias(name=alias.name, alias_type=alias.alias_type, source=alias, is_reverse=False)
            for alias in self.aliases.all()
        ]
        reverse = [
            EffectiveAlias(name=alias.author.name, alias_type=alias.alias_type, source=alias, is_reverse=True)
            for alias in AuthorAlias.objects.filter(name=self.name).exclude(author=self).select_related("author")
        ]
        return forward + reverse

    def get_transitive_aliases(self):
        """推移的な関係解決を含む別名一覧を返す（#1005）

        直接の関係（1ホップ、正方向・逆方向とも）はalias_typeを問わず必ず含む。
        alias_typeが"another"（別名義）・"group"（グループ）の関係は、そこから先の
        推移（2ホップ目以降の中継点）には使わない。それ以外の種別（id/abbr/common/
        past/sns/spell）は中継点として使え、そちら経由でさらに先のノードを発見する。

        循環（A-B-Aのような閉路）が発生しても、訪問済みノード（名前）を記録して
        無限ループ・重複を防ぐ。

        訪問するノード数に比例してクエリが発行される（各ノードごとに正方向・逆方向で
        最大2クエリ、正方向かつ中継可能な場合はさらにAuthor検索が1クエリ発行される）
        ため、巨大なクラスタに対して呼び出すとコストが大きくなる点に注意すること。

        各エントリのTransitiveAlias.author_idには、可能な範囲で追加クエリなしに
        解決できたauthor idを設定する（逆方向は所有者自身が実体のためselect_related
        済みのデータから、正方向かつ中継可能な種別は中継探索のためどのみち発行される
        Author検索から、それぞれ追加コストなしに取得する）。正方向かつ中継不可な種別
        （another/group）は中継探索を行わないため解決されず、Noneのままになる。
        呼び出し側でこの名前に対応するAuthorの有無が必要な場合は、author_idがNoneの
        エントリに限定して補完的に問い合わせること（#1023）。
        """
        visited_names = {self.name}
        results = []
        queue = deque([(self.name, self)])

        while queue:
            current_name, current_author = queue.popleft()
            is_direct = current_name == self.name
            for target_name, alias_type, source, is_reverse in get_alias_edges(current_name, current_author):
                if target_name in visited_names:
                    continue
                visited_names.add(target_name)

                if is_reverse:
                    # 逆方向はこの行の所有者(source.author)がtarget_nameの実体そのもの。
                    # get_alias_edges()内でselect_related済みのため追加クエリは発生しない
                    target_author = source.author
                elif alias_type not in NON_BRIDGING_ALIAS_TYPES:
                    # 正方向かつ中継可能な種別のみ、中継探索のためにAuthorを解決する
                    target_author = Author.get_by_name(target_name)
                else:
                    target_author = None

                results.append(TransitiveAlias(
                    name=target_name,
                    alias_type=alias_type,
                    source=source,
                    is_reverse=is_reverse,
                    is_direct=is_direct,
                    author_id=target_author.id if target_author is not None else None,
                ))
                if alias_type not in NON_BRIDGING_ALIAS_TYPES:
                    queue.append((target_name, target_author))

        return results


# 曲の作者のwebページの情報
class AuthorLink(models.Model):
    url = models.CharField(max_length = 100)
    author = models.ForeignKey(Author, on_delete = models.CASCADE, null=True, related_name="links")


# 曲の作者の別の呼び方の情報
# nameがauthor.nameに対して双方向に別名をつける（Author.get_effective_aliases()参照）。
# 曲の検索(subekashi/lib/query_filters.py)やAuthorの別名一覧画面で利用される
class AuthorAlias(models.Model):
    CHOICES = (
        ("id", "ID"),
        ("abbr", "略称"),
        ("common", "通称"),
        ("past", "以前の名称"),
        ("sns", "SNSでの名称"),
        ("spell", "表記揺れ"),
        # 同一人物が運用している、本人公認の別名義（#1004）
        ("another", "別名義"),
        ("group", "グループ"),
    )

    name = models.CharField(max_length = 500)
    alias_type = models.CharField(default = "another", choices=CHOICES, max_length=10)
    author = models.ForeignKey(Author, on_delete = models.CASCADE, related_name="aliases")

    class Meta:
        # 【MySQL移行時の注意】(#1044)
        # 下記のUniqueConstraint(condition=...)は「部分インデックス」であり、
        # SQLite・PostgreSQLではサポートされるが、MySQLではDjangoが未サポートのため
        # 実際のDB制約としては作成されない（`python manage.py check`でmodels.W036の
        # system check warningが出るのみで、例外にはならず静かにスキップされる）。
        # 現状（config/settings.pyのUSE_MYSQL=False）はSQLite上で実際にDBレベルの
        # 重複防止が効いているが、将来USE_MYSQL=Trueに切り替える際は、切り替え前に
        # USE_MYSQL=Trueの設定で`python manage.py check`を実行しW036が出ないか
        # 必ず確認すること。W036が出る場合、MySQL上ではこの制約が効かず
        # AuthorAliasForm.clean()のアプリ層チェックのみが重複防止の頼りになる
        # （views/author_alias.pyのTOCTOU対策用IntegrityError catchも同時に
        # 無効化される点に注意。DBレベルでの完全な保証が必要になった場合は、
        # MySQLでも通常のユニークインデックスとして効く生成列などの
        # ワークアラウンドを別途検討すること）
        constraints = [
            # alias_type="group"（合作アカウント等、複数人で運用している名義）以外は
            # 従来通りnameをグローバルにユニークとする（#1044）
            models.UniqueConstraint(
                fields=["name"],
                condition=~models.Q(alias_type="group"),
                name="unique_authoralias_name_except_group",
            ),
            # alias_type="group"は複数のauthorが同じグループ名を登録できるようにするため、
            # (name, author)単位でのみユニークとする（同じauthorによる重複登録のみ防ぐ）
            models.UniqueConstraint(
                fields=["name", "author"],
                condition=models.Q(alias_type="group"),
                name="unique_authoralias_name_author_for_group",
            ),
        ]

    def __str__(self):
        return self.name


@dataclass
class EffectiveAlias:
    """Author.get_effective_aliases()が返す、双方向解決済みの別名1件分の情報

    is_reverse=Trueの場合、sourceは他のauthorが所有するAuthorAliasであり編集・削除の対象にはできない
    """
    name: str
    alias_type: str
    source: AuthorAlias
    is_reverse: bool = False

    @property
    def alias_type_display(self):
        return dict(AuthorAlias.CHOICES).get(self.alias_type, self.alias_type)


@dataclass
class TransitiveAlias:
    """Author.get_transitive_aliases()が返す、推移的関係解決済みの別名1件分の情報

    is_direct=Trueかつis_reverse=Falseの場合のみ、sourceは呼び出し元のauthorが
    直接所有するAuthorAliasであり編集・削除の対象にできる。それ以外（is_direct=False、
    またはis_reverse=True）の場合、sourceは他のauthorが所有するAuthorAliasであり
    編集・削除の対象にはできない。

    is_reverseはこのエントリを発見した最後の1ホップの向き（正方向か逆方向か）を表し、
    alias_type="group"の場合の表示ラベルの出し分け（所属グループ/所属している名義）、
    alias_type="past"の場合の表示ラベルの出し分け（以前の名称/その後の名称、#1019）にも使う。

    author_idはnameに対応する実在Authorのid（存在しない場合はNone）。
    get_transitive_aliases()が追加クエリなしに解決できた範囲でのみ設定され、
    正方向かつalias_typeが"another"・"group"のエントリは常にNoneになる（#1023）。
    """
    name: str
    alias_type: str
    source: AuthorAlias
    is_reverse: bool = False
    is_direct: bool = False
    author_id: int = None

    @property
    def alias_type_display(self):
        if self.alias_type == "group":
            return "所属している名義" if self.is_reverse else "所属グループ"
        if self.alias_type == "past" and self.is_reverse:
            return "その後の名称"
        return dict(AuthorAlias.CHOICES).get(self.alias_type, self.alias_type)
