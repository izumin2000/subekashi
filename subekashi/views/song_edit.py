from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.search import song_search
from urllib.parse import urlparse


def song_edit(request, song_id) :
    try :
        song = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    dataD = {
        "metatitle": f"{song.title}の編集",
        "song": song,
    }

    if request.method == "POST":
        title = request.POST.get("title", "")
        channel = request.POST.get("channel", "")
        url = request.POST.get("url", "")
        imitates = request.POST.get("imitate", "")
        lyrics = request.POST.get("lyrics", "")
        is_original = bool(request.POST.get("is-original"))
        is_deleted = bool(request.POST.get("is-deleted"))
        is_joke = bool(request.POST.get("is-joke"))
        is_inst = bool(request.POST.get("is-inst"))
        is_subeana = bool(request.POST.get("is-subeana"))
        is_draft = bool(request.POST.get("is-draft"))
        
        # 既に登録されているURLの場合はエラー
        cleaned_url = clean_url(url)
        cleaned_url_list = cleaned_url.split(",") if cleaned_url else []
        for cleaned_url_item in cleaned_url_list:
            existing_song, _ = song_search({"url": cleaned_url_item})
            if url and existing_song.exists() and existing_song.first().id != song_id :
                dataD["error"] = "URLは既に登録されています。"
                return render(request, 'subekashi/song_edit.html', dataD)
            
            domain = urlparse(cleaned_url_item).netloc
            is_safe = any([bool(re.search(allow_pattern, domain)) for allow_pattern in URL_ICON.keys()])
            if not is_safe:
                contact_url = reverse('subekashi:contact')
                dataD["error"] = f"URL：{cleaned_url_item}は信頼されていないURLと判断されました。<br>\
                <a href='{contact_url}?&category=提案&detail={cleaned_url_item} を登録できるようにしてください。' target='_blank'>お問い合わせ</a>にて、\
                該当のURLを登録できるように、ご連絡ください。"
                return render(request, 'subekashi/song_edit.html', dataD)

        # タイトルとチャンネルが空の場合はエラー
        if ("" in [title, channel]) :
            dataD["error"] = "タイトルかチャンネルが空です。"
            return render(request, 'subekashi/song_edit.html', dataD)
        
        # DB保存用に変数を用意
        ip = get_ip(request)
        cleand_title = title.replace(" ,", ",").replace(", ", ",")
        cleand_channel = channel.replace("/", "╱").replace(" ,", ",").replace(", ", ",")
        cleand_lyrics = lyrics.replace("\r\n", "\n")

        # discordに通知
        content = f'\n\
        編集されました\n\
        {ROOT_URL}/songs/{song_id}\n\
        タイトル：{cleand_title}\n\
        チャンネル : {cleand_channel}\n\
        URL : {cleaned_url}\n\
        ネタ曲 : {"Yes" if is_joke else "No"}\n\
        すべあな模倣曲 : {"Yes" if is_subeana else "No"}\n\
        IP : {ip}\n\
        歌詞 : ```{cleand_lyrics}```\n\
        '
        is_ok = send_discord(NEW_DISCORD_URL, content)
        if not is_ok:
            song.delete()
            return render(request, 'subekashi/500.html', status=500)

        # 新しい模倣の追加
        old_imitate_id_set = set(song.imitate.split(",")) - set([""])       # 元々の各模倣のID
        new_imitate_id_set = set(imitates.split(",")) - set([""])       # ユーザーが入力した各模倣のID

        append_imitate_id_set = new_imitate_id_set - old_imitate_id_set     # 編集によって新しく追加された各模倣のID
        delete_imitate_id_set = old_imitate_id_set - new_imitate_id_set     # 編集によって削除された各模倣のID

        # 編集によって新しく追加された各模倣先の被模倣に編集した曲のsong_idを追加する
        for append_imitate_id in append_imitate_id_set :
            append_imitate = Song.objects.get(pk = append_imitate_id)
            append_imitated_id_set = set(append_imitate.imitated.split(","))        # 模倣先の被模倣
            append_imitated_id_set.add(str(song_id))        # 模倣先の被模倣に編集した曲のsong_idを追加する
            
            append_imitate.imitated = ",".join(append_imitated_id_set).strip(",")
            append_imitate.save()
            
        # 編集によって削除された各模倣先の被模倣に編集した曲のsong_idを削除する
        for delete_imitate_id in delete_imitate_id_set :
            delete_imitate = Song.objects.get(pk = delete_imitate_id)
            delete_imitated_id_set = set(delete_imitate.imitated.split(","))        # 模倣先の被模倣
            delete_imitated_id_set.remove(str(song_id))   # 被模倣に編集した曲のsong_idを削除する
                        
            delete_imitate.imitated = ",".join(delete_imitated_id_set).strip(",")
            delete_imitate.save()

        # songの更新
        song.title = cleand_title
        song.channel = cleand_channel
        song.url = cleaned_url
        song.lyrics = cleand_lyrics
        song.imitate = imitates
        song.isoriginal = is_original
        song.isdeleted = is_deleted
        song.isjoke = is_joke
        song.isinst = is_inst
        song.issubeana = is_subeana
        song.isdraft = is_draft
        song.post_time = timezone.now()
        song.ip = ip
        song.save()
        
        return redirect(f'/songs/{song_id}?toast=edit')
    return render(request, 'subekashi/song_edit.html', dataD)
