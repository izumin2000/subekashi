from django.shortcuts import render, redirect
from django.utils import timezone
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.search import song_search


def song_edit(request, song_id) :
    try :
        song_obj = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    MAX_META_TITLE = 25
    metatitle = f"{song_obj.title}の編集" if len(song_obj.title) < MAX_META_TITLE else f"{song_obj.title[:MAX_META_TITLE]}...の編集"
    dataD = {
        "metatitle": metatitle,
        "song": song_obj,
    }

    if request.method == "POST":
        title = request.POST.get("title")
        channel = request.POST.get("channel")
        url = request.POST.get("url")
        imitates = request.POST.get("imitate")
        lyrics = request.POST.get("lyrics")
        is_original = bool(request.POST.get("is-original"))
        is_deleted = bool(request.POST.get("is-deleted"))
        is_joke = bool(request.POST.get("is-joke"))
        is_inst = bool(request.POST.get("is-inst"))
        is_subeana = bool(request.POST.get("is-subeana"))
        is_draft = bool(request.POST.get("is-draft"))
        
        # 既に登録されているURLの場合はエラー
        cleaned_url = clean_url(url)
        cleaned_url_list = cleaned_url.split(",")
        for cleaned_url_item in cleaned_url_list:
            existing_song, _ = song_search({"url": cleaned_url_item})
            if url and existing_song.exists() and existing_song.first().id != song_id :
                return render(request, "subekashi/500.html", status=500)

        # タイトルとチャンネルが空の場合はエラー
        if ("" in [title, channel]) :
            return render(request, "subekashi/500.html", status=500)
        
        # DB保存用に変数を用意
        ip = get_ip(request)
        cleand_channel = channel.replace("/", "╱")
        cleand_lyrics = lyrics.replace("\r\n", "\n")

        # discordに通知
        content = f'\n\
        編集されました\n\
        {ROOT_URL}/songs/{song_id}\n\
        タイトル：{title}\n\
        チャンネル : {cleand_channel}\n\
        URL : {cleaned_url}\n\
        ネタ曲 : {"Yes" if is_joke else "False"}\n\
        すべあな模倣曲 : {"Yes" if is_subeana else "False"}\n\
        IP : {ip}```'
        # is_ok = sendDiscord(NEW_DISCORD_URL, content)
        # if not is_ok:
        #     song_obj.delete()
        #     return render(request, 'subekashi/500.html', status=500)

        # 新しい模倣の追加
        old_imitate_id_set = set(song_obj.imitate.split(",")) - set([""])       # 元々の各模倣のID
        new_imitate_id_set = set(imitates.split(",")) - set([""])       # ユーザーが入力した各模倣のID

        append_imitate_id_set = new_imitate_id_set - old_imitate_id_set     # 編集によって新しく追加された各模倣のID
        delete_imitate_id_set = old_imitate_id_set - new_imitate_id_set     # 編集によって削除された各模倣のID

        # 編集によって新しく追加された各模倣先の被模倣に編集した曲のsong_idを追加する
        for append_imitate_id in append_imitate_id_set :
            append_imitate = Song.objects.get(pk = append_imitate_id)
            append_imitated_id_set = set(append_imitate.imitated.split(","))        # 模倣先の被模倣
            append_imitated_id_set.add(str(song_id))        # 模倣先の被模倣に編集した曲のsong_idを追加する
            
            append_imitate.imitated = ",".join(append_imitated_id_set)
            append_imitate.save()
            
        # 編集によって削除された各模倣先の被模倣に編集した曲のsong_idを削除する
        for delete_imitate_id in delete_imitate_id_set :
            delete_imitate = Song.objects.get(pk = delete_imitate_id)
            delete_imitated_id_set = set(delete_imitate.imitated.split(","))        # 模倣先の被模倣
            delete_imitated_id_set.remove(str(song_id))   #   被模倣に編集した曲のsong_idを削除する
                        
            delete_imitate.imitated = ",".join(delete_imitated_id_set)
            delete_imitate.save()

        # song_objの更新
        song_obj.title = title
        song_obj.channel = cleand_channel
        song_obj.url = cleaned_url
        song_obj.lyrics = cleand_lyrics
        song_obj.imitate = imitates
        song_obj.isoriginal = is_original
        song_obj.isdeleted = is_deleted
        song_obj.isjoke = is_joke
        song_obj.isinst = is_inst
        song_obj.issubeana = is_subeana
        song_obj.isdraft = is_draft
        song_obj.post_time = timezone.now()
        song_obj.ip = ip
        song_obj.save()
        
        return redirect(f'/songs/{song_id}')
    return render(request, 'subekashi/song_edit.html', dataD)
