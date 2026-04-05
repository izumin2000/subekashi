from django.shortcuts import render, redirect
from django.views import View
from subekashi.models import Song, Editor, History
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.song_service import build_delete_discord_text
from config.local_settings import DELETE_DISCORD_URL


class SongDeleteView(View):
    def dispatch(self, request, song_id, *args, **kwargs):
        self.song = Song.get_or_none(song_id)
        if self.song is None:
            return render(request, 'subekashi/404.html', status=404)
        if self.song.is_lock:
            return redirect(f'/songs/{song_id}?toast=lock')
        return super().dispatch(request, song_id, *args, **kwargs)

    def get_base_context(self):
        return {
            "metatitle": f"{self.song.title}の削除申請",
            "song": self.song,
        }

    def get(self, request, song_id):
        return render(request, "subekashi/song_edit.html", self.get_base_context())

    def post(self, request, song_id):
        context = self.get_base_context()
        reason = request.POST.get("reason", "")

        # もし削除理由を入力していないのならやり直し
        if not reason:
            context["error"] = "削除理由を入力してください。"
            return render(request, "subekashi/song_edit.html", context)

        # 編集履歴を保存
        ip = get_ip(request)
        editor = Editor.get_or_create_from_ip(ip)

        History.create_for_song(
            song=self.song,
            title=f"{self.song.title}を削除申請",
            history_type="delete",
            changes=["理由", reason],
            editor=editor,
        )

        # Discordに送信
        content = build_delete_discord_text(self.song, reason, editor)
        is_ok = send_discord(DELETE_DISCORD_URL, content)
        if not is_ok:
            context["error"] = "お問い合わせを送信できませんでした。"
            return render(request, 'subekashi/song_edit.html', context)

        # レンダリング
        return redirect(f'/songs/{song_id}?toast=delete')
