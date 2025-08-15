from django.db import models
from django.utils import timezone


# SongやChannelを編集したユーザーのIPアドレスの情報
# 画面上では"全て{song_id}の所為です。"と表示される
class Editor(models.Model):
    ip = models.CharField(default = "", unique=True, max_length = 100)
    
    def __str__(self):
        return f"全て{self.id}の所為です。"


# 楽曲のメイン情報
# editor以外の外部キーはまだ無いので後ほどカスタムコマンドで対応を行う
class Song(models.Model):
    CHOICES = (
        ("song", "曲"),
        ("arrange", "アレンジ"),
        ("otomad", "音MAD"),
        ("medley", "メドレー"),
        ("omnibus", "総集編"),
        ("notice", "告知"),
        ("dec", "解読"),
        ("offv", "オフボ"),
        ("cover", "カバー"),
        ("joke", "ネタ動画"),
        ("other", "その他"),
    )
    
    title = models.CharField(default = "", max_length = 500)
    channel = models.CharField(default = "", max_length = 500)      # TODO Channelテーブルの利用
    url = models.CharField(blank = True, null = True, default = "", max_length = 500)       # TODO URLテーブルの利用
    lyrics = models.TextField(blank = True, null = True, default = "", max_length = 10000)
    # imitates = models.ManyToManyField("self", symmetrical=False, related_name="imitateds", blank=True)     # TODO 自己参照
    imitate = models.CharField(blank = True, null = True, default = "", max_length = 10000)
    imitated = models.CharField(blank = True, null = True, default = "", max_length = 10000)
    post_time = models.DateTimeField(default = timezone.now)
    upload_time = models.DateTimeField(blank = True, null = True)
    isoriginal = models.BooleanField(default = False)       # TODO is_
    isjoke = models.BooleanField(default = False)
    isdeleted = models.BooleanField(default = False)
    isdraft = models.BooleanField(default = False)
    isinst = models.BooleanField(default = False)
    issubeana = models.BooleanField(default = True)
    isspecial = models.BooleanField(default = False)
    islock = models.BooleanField(default = False)
    ip = models.CharField(default = "", max_length = 100)
    view = models.IntegerField(blank = True, null = True)
    like = models.IntegerField(blank = True, null = True)
    category = models.CharField(default = "song", choices=CHOICES, max_length=10)
    editor = models.ForeignKey(Editor, on_delete = models.CASCADE, null=True, related_name="songs")

    def __str__(self):
        return self.title
    
    # TODO save処理のオーバーライドメソッド
    # def save(self, *args, **kwargs):
        # super().save(*args, **kwargs)
    
    # def channels(self):
        # return
    
    # def urls(self):
        # return
    
    # def imitates(self):
        # return

# 曲のURLの情報
# urlは許可したメディア(YouTube, niconico等)のurlしか受け付けないことを想定
class SongLink(models.Model):
    url = models.CharField(default = "", max_length = 100)        # TODO 全削除申請対応後uniqueにする
    song = models.ForeignKey(Song, on_delete = models.CASCADE, related_name="links")


# 曲の作者の情報
# TODO Channel -> Author, チャンネル名 -> 作者
class Channel(models.Model):
    name = models.CharField(unique=True, max_length = 500)

    def __str__(self):
        return self.name
    
    # def save(self, *args, **kwargs):
        # super().save(*args, **kwargs)


# 曲の作者のwebページの情報
class ChannelLink(models.Model):
    url = models.CharField(max_length = 100)
    channel = models.ForeignKey(Channel, on_delete = models.CASCADE, null=True, related_name="links")


# 曲の作者の別の呼び方の情報
# 曲の登録時や編集時に正式な呼び方(channel.name)に変更するために使用される
class ChannelAlias(models.Model):
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
    channel = models.ForeignKey(Channel, on_delete = models.CASCADE, related_name="aliases")

    def __str__(self):
        return self.name
    
    # def save(self, *args, **kwargs):
        # super().save(*args, **kwargs)


# ユーザーによる曲や作者の変更を記録した情報
# changeは編集内容をマークダウンで記録する
class History(models.Model):
    CHOICES = (
        ("new", "新規作成"),
        ("edit", "編集"),
        ("delete", "削除申請"),
    )
    
    song = models.ForeignKey(Song, blank = True, null = True, on_delete = models.SET_NULL, related_name="histories")
    title = models.CharField(default = "", max_length = 100)
    edit_type = models.CharField(default = "new", choices=CHOICES, max_length = 10)
    edited_time = models.DateTimeField(default = timezone.now)
    changes = models.CharField(default = "", max_length = 20000)
    editor = models.ForeignKey(Editor, on_delete = models.CASCADE, related_name="histories")


# すべかしへの問い合わせとその回答の情報
class Contact(models.Model):
    detail = models.TextField(max_length = 10000)
    post_time = models.DateField()
    answer = models.TextField(blank = True, null = True, max_length = 10000)
    
    def __str__(self):
        return self.detail[:30]


# 正常に狂うのです。が生成した歌詞の情報
class Ai(models.Model):
    lyrics = models.CharField(default = "", max_length = 100)
    score = models.IntegerField(default = 0)
    genetype = models.CharField(default = "", max_length = 100)
    
    def __str__(self):
        return self.lyrics


# すべかしDSPに登録された曲の情報
class Ad(models.Model):
    CHOICES = (
        ("still", "未審査"),
        ("pass", "公開中"),
        ("fail", "未通過"),
    )
    url = models.CharField(default = "", max_length = 100)
    view = models.IntegerField(default = 0)
    click = models.IntegerField(default = 0)
    dup = models.IntegerField(default = 0)
    status = models.CharField(default = "still", choices=CHOICES, max_length=10)
    
    def __str__(self):
        return self.url