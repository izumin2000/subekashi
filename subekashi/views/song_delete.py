from django.shortcuts import render, redirect
from subekashi.models import Song, Editor, History
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.song_service import build_delete_discord_text
from config.local_settings import DELETE_DISCORD_URL


def song_delete(request, song_id):
    # 曲が存在しないなら404を返す
    song = Song.get_or_none(song_id)
    if song is None:
        return render(request, 'subekashi/404.html', status=404)

    # 曲が編集不可能なら編集画面に遷移せずロックトーストを表示する
    if song.is_lock:
        return redirect(f'/songs/{song_id}?toast=lock')

    dataD = {
        "metatitle": f"{song.title}の削除申請",
        "song": song
    }

    if request.method == "POST":
        reason = request.POST.get("reason", "")

        # もし削除理由を入力していないのならやり直し
        if not reason:
            dataD["error"] = "削除理由を入力してください。"
            return render(request, "subekashi/song_edit.html", dataD)

        # 編集履歴を保存
        ip = get_ip(request)
        editor = Editor.get_or_create_from_ip(ip)

        History.create_for_song(
            song=song,
            title=f"{song.title}を削除申請",
            history_type="delete",
            changes=["理由", reason],
            editor=editor,
        )

        # Discordに送信
        content = build_delete_discord_text(song, reason, editor)
        is_ok = send_discord(DELETE_DISCORD_URL, content)
        if not is_ok:
            dataD["error"] = "お問い合わせを送信できませんでした。"
            return render(request, 'subekashi/song_edit.html', dataD)

        # レンダリング
        return redirect(f'/songs/{song_id}?toast=delete')

    return render(request, "subekashi/song_edit.html", dataD)
