from dataclasses import dataclass
from django.db import models
from .base import GetOrNoneMixin


# 曲の作者の情報
class Author(GetOrNoneMixin, models.Model):
    name = models.CharField(unique=True, max_length = 500)

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


# 曲の作者のwebページの情報
class AuthorLink(models.Model):
    url = models.CharField(max_length = 100)
    author = models.ForeignKey(Author, on_delete = models.CASCADE, null=True, related_name="links")


# 曲の作者の別の呼び方の情報
# 曲の登録時や編集時に正式な呼び方(author.name)に変更するために使用される
class AuthorAlias(models.Model):
    CHOICES = (
        ("id", "ID"),
        ("abbr", "略称"),
        ("common", "通称"),
        ("past", "以前の名称"),
        ("sns", "SNSでの名称"),
        ("spell", "表記揺れ"),
        ("another", "別名義"),
    )

    name = models.CharField(unique=True, max_length = 500)
    alias_type = models.CharField(default = "another", choices=CHOICES, max_length=10)
    author = models.ForeignKey(Author, on_delete = models.CASCADE, related_name="aliases")

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
