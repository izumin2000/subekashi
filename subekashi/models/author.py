from django.db import models


# 曲の作者の情報
class Author(models.Model):
    name = models.CharField(unique=True, max_length = 500)

    def __str__(self):
        return self.name

    @classmethod
    def get_or_none(cls, pk):
        try:
            return cls.objects.get(pk=pk)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_name(cls, name):
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            return None


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
        ("other", "別名義"),
    )

    name = models.CharField(unique=True, max_length = 500)
    alias_type = models.CharField(default = "other", choices=CHOICES, max_length=10)
    author = models.ForeignKey(Author, on_delete = models.CASCADE, related_name="aliases")

    def __str__(self):
        return self.name
