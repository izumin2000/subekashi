from django.db import models


# 全て蛇の目の所為です。が作成した歌詞の情報
class Ai(models.Model):
    # 単語入れ替え（janome）で作成されたAiレコードのgenetype。
    # レガシーのGPTインポート（"model"）は廃止済みのため、現在使われるのはこれのみ
    GENETYPE_JANOME = "janome"

    lyrics = models.CharField(default = "", max_length = 100)
    score = models.IntegerField(default = 0)
    genetype = models.CharField(default = "", max_length = 100)

    class Meta:
        # 【MySQL移行時の注意】(#593)
        # 下記のUniqueConstraint(condition=...)は「部分インデックス」であり、
        # SQLite・PostgreSQLではサポートされるが、MySQLではDjangoが未サポートのため
        # 実際のDB制約としては作成されない（`python manage.py check`でmodels.W036の
        # system check warningが出るのみで、例外にはならず静かにスキップされる）。
        # その場合、AiWordSwapView/manage.py aiのget_or_create()による重複防止は
        # アプリ層のみの保証となり、ほぼ同時に同じ入れ替え結果がPOSTされた場合の
        # TOCTOU対策が効かなくなる。詳細はsubekashi/models/author.pyの同種コメントを参照
        constraints = [
            # genetype="janome"のみを対象にする（レガシーgenetype="model"等には
            # 既に(lyrics, genetype)の重複が存在するため、全genetype共通の制約には出来ない）
            models.UniqueConstraint(
                fields=["lyrics"],
                # Metaのネストしたクラス本体からはクラス変数GENETYPE_JANOMEを
                # 直接参照できない（Pythonの仕様上、入れ子クラスは外側のクラス
                # スコープを継承しない）ため、リテラル文字列を直接指定する
                condition=models.Q(genetype="janome"),
                name="unique_janome_lyrics",
            ),
        ]

    def __str__(self):
        return self.lyrics

    @classmethod
    def get_top_scored(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME, score=5)

    @classmethod
    def get_high_scored_janome(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME, score=5).order_by('?')[:300]

    @classmethod
    def get_unscored_janome(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME, score=0)

    @classmethod
    def get_all_janome(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME)
