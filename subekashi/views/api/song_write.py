import copy
import re
import unicodedata
from collections.abc import Mapping
from html import unescape
from urllib.parse import parse_qs, urlsplit
from django.http import QueryDict
from django.utils.html import strip_tags
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from subekashi.views.song_delete import SongDeleteView
from subekashi.views.song_edit import SongEditView
from subekashi.views.song_new import SongNewView

# 曲のAPIの登録・変更・削除（#973）は、画面と同じビューを実行する。バリデーションや保存、履歴・Discordへの通知もビューに任せるため、
# ここではAPIのリクエストをビューのPOSTに、ビューの応答をJSONに変換するだけにする

NEW_FIELDS = ("title", "authors", "url", "allow_dup_url", "category")
NEW_FLAGS = ("is_original", "is_deleted", "is_joke", "is_inst", "is_subeana", "is_questionable")
EDIT_FIELDS = ("title", "authors", "url", "allow_dup_url", "imitate", "lyrics", "category")
EDIT_FLAGS = ("is_original", "is_deleted", "is_joke", "is_inst", "is_subeana", "is_draft", "is_questionable")

LOCK_ERROR = "この曲はロックされているため、変更できません。"
NOT_FOUND_ERROR = "曲が見つかりません。"
REMOVED_ERROR = "この曲は削除されています。"
SERVER_ERROR = "処理中にエラーが発生しました。"


# 画面用のビューはエラーをcontext["error"]に入れてHTMLを返す。APIではビューの実行後にそのエラーを取り出してJSONで返す
class ContextRecordingMixin:
    context = None

    def get_base_context(self):
        self.context = super().get_base_context()
        return self.context


# 新規登録のエラーはテンプレートがエスケープして表示するため、文字列はそのままの文章
class SongNewAPIView(ContextRecordingMixin, SongNewView):
    error_is_html = False


# 編集のテンプレートは{{ error|safe }}で表示するため、エラーはリンク（<a>）を含んだり、入力値をエスケープしたHTMLになっている
class SongEditAPIView(ContextRecordingMixin, SongEditView):
    error_is_html = True


class SongDeleteAPIView(ContextRecordingMixin, SongDeleteView):
    error_is_html = False


def to_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = ",".join(str(item) for item in value)
    # NormalizePostDataMiddlewareは、JSONのリクエストのPOSTには届かないため、濁点・半濁点の正規化をここで行う
    return unicodedata.normalize("NFC", str(value))


def to_flag(name, value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise ValidationError({"error": f"{name}は真偽値で指定してください。"})


def get_request_data(request):
    if not isinstance(request.data, Mapping):
        raise ValidationError({"error": "リクエストはJSONのオブジェクトで指定してください。"})
    return request.data


# 登録は画面の「タイトルと作者から登録」のチェックボックス（is-original-manualなど）に対応させる。
# 界隈曲?（is_subeana）は画面の初期値と同じく、指定が無ければTrueにする
def build_new_post_data(data):
    post_data = QueryDict(mutable=True)
    for field in NEW_FIELDS:
        if field in data:
            post_data[field] = to_text(data[field])
    for flag in NEW_FLAGS:
        if to_flag(flag, data.get(flag, flag == "is_subeana")):
            post_data[f"{flag.replace('_', '-')}-manual"] = "on"
    return post_data


# 編集画面のフォームは、送られなかった項目を空（歌詞は消え、フラグはFalse）として保存するため、
# 指定が無い項目は今の曲の値で補い、一部の項目だけを変更できるようにする
def build_edit_post_data(data, song):
    values = {
        "title": song.title,
        "authors": song.authors_str(","),
        "url": list(song.links.values_list("url", flat=True)),
        "imitate": list(song.imitates.values_list("id", flat=True)),
        "lyrics": song.lyrics,
        "category": song.category,
        **{flag: getattr(song, flag) for flag in EDIT_FLAGS},
    }
    values.update({field: data[field] for field in (*EDIT_FIELDS, *EDIT_FLAGS) if field in data})

    post_data = QueryDict(mutable=True)
    for field in EDIT_FIELDS:
        if field in values:
            post_data[field] = to_text(values[field])
    for flag in EDIT_FLAGS:
        if to_flag(flag, values[flag]):
            post_data[flag] = "on"
    return post_data


def build_delete_post_data(data):
    post_data = QueryDict(mutable=True)
    post_data["reason"] = to_text(data.get("reason"))
    return post_data


def run_view(view_class, request, post_data, **kwargs):
    # 画面のビューはPOSTのフォームを読むため、フォームを送信したリクエストとして実行する
    django_request = copy.copy(request._request)
    django_request.method = "POST"
    django_request.POST = post_data
    view = view_class()
    view.setup(django_request, **kwargs)
    return view, view.dispatch(django_request, **kwargs)


def to_plain_text(message, is_html):
    if is_html:
        message = unescape(strip_tags(message))
    return " ".join(message.split())


# ビューが失敗していればそのエラーのResponseを、成功していればNoneを返す
def build_error_response(view, response):
    error = (view.context or {}).get("error")
    if error:
        return Response({"error": to_plain_text(error, view.error_is_html)}, status=status.HTTP_400_BAD_REQUEST)

    if response.status_code == 302:
        # ロックされた曲は、トーストでロックを知らせるページに遷移する
        query = parse_qs(urlsplit(response["Location"]).query)
        if query.get("toast") == ["lock"]:
            return Response({"error": LOCK_ERROR}, status=status.HTTP_403_FORBIDDEN)
        return None
    if response.status_code == 404:
        return Response({"error": NOT_FOUND_ERROR}, status=status.HTTP_404_NOT_FOUND)
    if response.status_code == 410:
        return Response({"error": REMOVED_ERROR}, status=status.HTTP_410_GONE)
    return Response({"error": SERVER_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 新規登録の成功は、登録した曲の編集画面（/songs/<id>/edit）へのリダイレクトになる
def get_created_song_id(response):
    match = re.match(r"^/songs/(\d+)/edit", response["Location"])
    return int(match.group(1))
