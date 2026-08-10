from django.db import models
from django.utils import timezone
from .song import Song
from .author import Author
from .editor import Editor


# ユーザーによる曲や作者の変更を記録した情報
# changeは編集内容をマークダウンで記録する
# songとauthorは排他的に使用する（曲の変更履歴はsongのみ、作者の変更履歴はauthorのみを設定する）
class History(models.Model):
    CHOICES = (
        ("new", "新規作成"),
        ("edit", "編集"),
        ("delete", "削除申請"),
    )

    song = models.ForeignKey(Song, blank = True, null = True, on_delete = models.SET_NULL, related_name="histories")
    author = models.ForeignKey(Author, blank = True, null = True, on_delete = models.SET_NULL, related_name="histories")
    title = models.CharField(default = "", max_length = 100)
    history_type = models.CharField(default = "new", choices=CHOICES, max_length = 10)
    create_time = models.DateTimeField(default = timezone.now)
    changes = models.JSONField(null=True, blank=True, default=None)
    editor = models.ForeignKey(Editor, on_delete = models.CASCADE, related_name="histories")

    @classmethod
    def create_for_song(cls, song, title, history_type, changes, editor):
        history = cls(
            song=song,
            title=title,
            history_type=history_type,
            create_time=timezone.now(),
            changes=changes,
            editor=editor,
        )
        history.save()
        return history

    @classmethod
    def create_for_author(cls, author, title, history_type, changes, editor):
        history = cls(
            author=author,
            title=title,
            history_type=history_type,
            create_time=timezone.now(),
            changes=changes,
            editor=editor,
        )
        history.save()
        return history

    @classmethod
    def get_for_song(cls, song):
        return cls.objects.select_related("editor").filter(song=song).order_by("-create_time")

    @classmethod
    def get_for_author(cls, author):
        return cls.objects.select_related("editor").filter(author=author).order_by("-create_time")

    @classmethod
    def get_for_editor(cls, editor):
        return cls.objects.select_related("song", "author").filter(editor=editor).order_by("-create_time")

    @classmethod
    def get_all(cls, search_query=""):
        qs = cls.objects.select_related("song", "author", "editor").order_by("-create_time")
        if search_query:
            qs = qs.filter(title__icontains=search_query)
        return qs
