from django.db import transaction
from django.shortcuts import render, redirect
from django.views import View
from subekashi.forms import SongRestoreForm
from subekashi.models import Song, Editor, History
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.song_service import build_restore_discord_text, get_restore_conflict_songs, restore_song
from subekashi.views.song_removed import render_song_removed
from config.local_settings import NEW_DISCORD_URL


# 削除した曲（#1239）のページの「削除を取り消す」ボタンから、曲の削除を取り消す（#1264）
class SongRestoreView(View):
    http_method_names = ['post']

    def post(self, request, song_id):
        with transaction.atomic():
            # 同時に押されたときに履歴・通知が二重にならないよう、曲の行をロックしてから確認する
            # 確認から取り消すまでの間に、別の曲の登録・編集で同じURLが登録されるとURLが重複しうるが、
            # 別の曲どうしで同じURLを同時に登録する場合（validate_song_url）と同じく、まれなため許容する
            song = Song.all_objects.select_for_update().filter(pk=song_id).first()
            if song is None:
                return render(request, 'subekashi/404.html', status=404)
            # 既に削除を取り消した曲は、曲のページに遷移する
            if not song.is_removed:
                return redirect(f'/songs/{song_id}')
            # ロックされた曲・URLが他の曲に登録されている曲は取り消さず、取り消せない理由を表示する
            if song.is_lock or get_restore_conflict_songs(song).exists():
                return render_song_removed(request, song)

            form = SongRestoreForm(request.POST)
            if not form.is_valid():
                return render_song_removed(request, song, error=form.errors['reason'][0])
            reason = form.cleaned_data['reason']

            editor = Editor.get_or_create_from_ip(get_ip(request))
            restore_song(song)
            History.create_for_song(
                song=song,
                title=f"{song.title}の削除を取り消し",
                history_type="restore",
                changes=["理由", reason],
                editor=editor,
            )

        # 通知に失敗しても削除は取り消されているため、500ページにはせず、取り消せたことと通知に失敗したことを伝える
        content = build_restore_discord_text(song, reason, editor)
        is_ok = send_discord(NEW_DISCORD_URL, content)

        response = redirect(f'/songs/{song_id}?toast=restore' if is_ok else f'/songs/{song_id}?toast=restore_notify_error')
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
