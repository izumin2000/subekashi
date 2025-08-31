from django.shortcuts import render, redirect
from django.utils import timezone
from subekashi.models import Song, Editor, History
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from config.settings import *


def song_delete(request, song_id):
    # 曲が存在しないなら404を返す
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)

    # 曲が編集不可能なら編集画面に遷移せずロックトーストを表示する
    if song.islock:
        return redirect(f'/songs/{song_id}?toast=lock')
    
    dataD = {
        "metatitle" : f"{song.title}の削除申請",
        "song": song
    }
    
    if request.method == "POST":
        reason = request.POST.get("reason", "")
        
        # もし削除理由を入力していないのならやり直し
        if not reason:
            dataD["result"] = "invalid"
            return render(request, "subekashi/song_delete.html", dataD)
        
        # 編集履歴を保存
        ip = get_ip(request)
        editor, _ = Editor.objects.get_or_create(ip = ip)
        
        history = History(
            song = song,
            title = f"{song.title}を削除申請",
            edit_type = "delete",
            edited_time = timezone.now(),
            changes = f"# {song.title}が削除申請されました\n**理由**: {reason}",
            editor = editor
        )
        history.save()
        
        # Discordに送信
        content = f' \
        ```{song.id}``` \n\
        {ROOT_URL}/songs/{song.id} \n\
        タイトル：{song.title}\n\
        チャンネル名：{song.channel}\n\
        理由：{reason}\n\
        編集者：{editor}\
        '
        is_ok = send_discord(DELETE_DISCORD_URL, content)
        if not is_ok:
            dataD["result"] = "error"
            return render(request, 'subekashi/song_delete.html', dataD)
        
        # レンダリング
        return redirect(f'/songs/{song_id}?toast=delete')
        
    return render(request, "subekashi/song_delete.html", dataD)