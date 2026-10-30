from django.db import transaction
from django.shortcuts import render, redirect
from django.views import View
from subekashi.constants.constants import BANNED_ERROR
from subekashi.forms import SongDeleteForm
from subekashi.models import Song, Editor, History
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.song_service import build_delete_discord_text, remove_song
from subekashi.views.song_removed import render_song_not_found
from config.local_settings import NEW_DISCORD_URL


class SongDeleteView(View):
    def dispatch(self, request, song_id, *args, **kwargs):
        self.song = Song.get_or_none(song_id)
        if self.song is None:
            return render_song_not_found(request, song_id)
        if self.song.is_lock:
            return redirect(f'/songs/{song_id}?toast=lock')
        return super().dispatch(request, song_id, *args, **kwargs)

    def get_base_context(self):
        return {
            "metatitle": f"{self.song.title}の削除",
            "song": self.song,
        }

    def get(self, request, song_id):
        return render(request, "subekashi/song_edit.html", self.get_base_context())

    def post(self, request, song_id):
        context = self.get_base_context()
        ip = get_ip(request)
        if Editor.is_banned_ip(ip):
            context["error"] = BANNED_ERROR
            return render(request, "subekashi/song_edit.html", context)

        form = SongDeleteForm(request.POST)

        if not form.is_valid():
            context["error"] = form.errors['reason'][0]
            return render(request, "subekashi/song_edit.html", context)

        reason = form.cleaned_data['reason']

        editor = Editor.get_or_create_from_ip(ip)

        # 曲を論理削除し、編集履歴を保存（#1239）
        with transaction.atomic():
            remove_song(self.song)
            History.create_for_song(
                song=self.song,
                title=f"{self.song.title}を削除",
                history_type="delete",
                changes=["理由", reason],
                editor=editor,
            )

        # 申請ではなく曲の変更になったため、新規登録・編集と同じ通知先のDiscordに送信する
        content = build_delete_discord_text(self.song, reason, editor)
        is_ok = send_discord(NEW_DISCORD_URL, content)

        # 削除した曲のページは表示できないため、トップに遷移する
        # 通知に失敗しても曲は削除されているため、500ページにはせず、削除できたことと通知に失敗したことを伝える
        return redirect('/?toast=delete' if is_ok else '/?toast=delete_notify_error')
