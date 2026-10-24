from urllib.parse import urlencode
from django.shortcuts import render
from django.urls import reverse
from config.settings import ROOT_URL
from subekashi.models import Song


# 曲が無ければ404を、ユーザーが削除した曲（#1239）なら、削除の取り消しをお問い合わせで申請するよう案内するページを返す
def render_song_not_found(request, song_id):
    if not Song.all_objects.filter(pk=song_id, is_removed=True).exists():
        return render(request, 'subekashi/404.html', status=404)

    query = urlencode({
        "category": "削除の取り消し",
        "detail": f"{ROOT_URL}/songs/{song_id} の削除を取り消してください。",
    })
    context = {
        "metatitle": "削除されたページ",
        "contact_url": f"{reverse('subekashi:contact')}?{query}",
    }
    return render(request, 'subekashi/song_removed.html', context, status=410)
