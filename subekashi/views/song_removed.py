from django.shortcuts import render
from subekashi.models import Song, History
from subekashi.lib.song_service import get_restore_conflict_songs


# 曲が無ければ404を、ユーザーが削除した曲（#1239）なら、削除を取り消すボタンのあるページを返す（#1264）
def render_song_not_found(request, song_id):
    song = Song.all_objects.filter(pk=song_id, is_removed=True).first()
    if song is None:
        return render(request, 'subekashi/404.html', status=404)
    return render_song_removed(request, song)


def render_song_removed(request, song, error=None):
    # 削除している間は編集できないため、最新の編集履歴が削除なら直近の削除の理由になる（管理サイトで削除した場合は履歴が無い）
    latest_history = History.get_for_song(song).first()
    is_delete = latest_history is not None and latest_history.history_type == "delete"
    # 削除の履歴のchangesは["理由", 理由]だが、管理サイト等で変えられていても410のページを500にしない
    changes = latest_history.changes if is_delete else None
    reason = changes[1] if isinstance(changes, list) and len(changes) > 1 else None

    context = {
        "metatitle": "削除されたページ",
        "song": song,
        "reason": reason,
        "conflict_songs": list(get_restore_conflict_songs(song)),
        "error": error,
    }
    response = render(request, 'subekashi/song_removed.html', context, status=410)
    # 削除を取り消した後にこのページをブラウザのキャッシュから表示しないよう、毎回サーバーに問い合わせる
    response['Cache-Control'] = 'no-cache'
    return response
