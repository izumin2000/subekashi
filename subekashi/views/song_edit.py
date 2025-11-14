from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse
from config.local_settings import NEW_DISCORD_URL
from config.settings import ROOT_URL
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.search import song_search


def song_edit(request, song_id):
    # Songがなければ404
    try :
        song = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    # 編集不可の場合は元の曲情報閲覧画面に戻してロックされていますトーストを表示
    if song.islock:
        return redirect(f'/songs/{song_id}?toast=lock')
    
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
        
        # URLのバリデーション
        cleaned_url = clean_url(url)
        cleaned_url_list = cleaned_url.split(",") if cleaned_url else []
        for cleaned_url_item in cleaned_url_list:
            # 既に登録されているURLの場合は(ユニークでなければ)エラー
            # TODO URLテーブルで実装したい
            existing_song, _ = song_search({"url": cleaned_url_item})
            if url and existing_song.exists() and existing_song.first().id != song_id :
                dataD["error"] = "URLは既に登録されています。"
                return render(request, 'subekashi/song_edit.html', dataD)
            
            # 許可されていないメディアのURLならばエラー
            if not get_allow_media(cleaned_url_item):
                contact_url = reverse('subekashi:contact')
                dataD["error"] = f"URL：{cleaned_url_item}は信頼されていないURLと判断されました。<br>\
                <a href='{contact_url}?&category=提案&detail={cleaned_url_item} を登録できるようにしてください。' target='_blank'>お問い合わせ</a>にて、\
                該当のURLを登録できるように、ご連絡ください。"
                return render(request, 'subekashi/song_edit.html', dataD)

        # タイトルとチャンネルが空の場合はエラー
        if ("" in [title, channel]) :
            dataD["error"] = "タイトルかチャンネルが空です。"
            return render(request, 'subekashi/song_edit.html', dataD)
        
        # DBに保存する値たち
        # TODO Channelテーブルを利用する
        # WARNING channelはそのままURLになるので/は別の文字╱に変換しないといけない
        ip = get_ip(request)
        cleaned_channel = channel.replace("/", "╱").replace(" ,", ",").replace(", ", ",")
        
        # 自分自身や重複している曲は模倣曲として登録できない
        imitates_list = set(imitates.split(","))
        imitates_list.discard(str(song_id))
        imitates = ",".join(list(imitates_list)) if imitates else ""
        
        # 掲載拒否リストの読み込み
        try:
            from subekashi.constants.dynamic.reject import REJECT_LIST
        except:
            REJECT_LIST = []
        
        # 掲載拒否チャンネルか判断する
        for check_channel in cleaned_channel.split(","):
            if not check_channel in REJECT_LIST:
                continue
            
            dataD["error"] = f"{check_channel}さんの曲は登録することができません。"
            return render(request, 'subekashi/song_new.html', dataD)

        # 新しい模倣の追加
        # TODO imitateテーブルを利用する
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
            if (delete_imitate_id != str(song_id)):
                delete_imitated_id_set.remove(str(song_id))   # 被模倣に編集した曲のsong_idを削除する
            
            delete_imitate.imitated = ",".join(delete_imitated_id_set).strip(",")
            delete_imitate.save()
        
        # 変更内容のマークダウンと送信するDiscordの文言の作成
        def yes_no(value):
            return "はい" if value else "いいえ"

        # song.imitateの形式をリンク付きタイトルの改行リストにする
        def Ids2Info(ids):
            song_id_list = ids.split(",") if ids else []
            info = ""
            for song_id in song_id_list:
                song = Song.objects.get(id = song_id)
                info += f"[{song.title}]({ROOT_URL}/songs/{song.id})\n"
            return info[:-1]        # 最後の改行は不要

        # songを更新する前にhistoryのために更新前後のsongの情報を記録しておく
        COLUMNS = [
            {"label": "タイトル", "before": song.title ,"after": title},
            {"label": "チャンネル名", "before": song.channel ,"after": cleaned_channel},
            {"label": "URL", "before": song.url ,"after": cleaned_url},
            {"label": "オリジナル", "before": yes_no(song.isoriginal) ,"after": yes_no(is_original)},
            {"label": "削除済み", "before": yes_no(song.isdeleted) ,"after": yes_no(is_deleted)},
            {"label": "ネタ曲", "before": yes_no(song.isjoke) ,"after": yes_no(is_joke)},
            {"label": "インスト曲", "before": yes_no(song.isinst) ,"after": yes_no(is_inst)},
            {"label": "すべあな模倣曲", "before": yes_no(song.issubeana) ,"after": yes_no(is_subeana)},
            {"label": "下書き", "before": yes_no(song.isdraft) ,"after": yes_no(is_draft)},
            {"label": "模倣", "before": Ids2Info(song.imitate), "after": Ids2Info(imitates)},
            {"label": "歌詞", "before": song.lyrics, "after": lyrics.replace("\r\n", "\n")},
        ]

        # songの更新
        song.title = title
        song.channel = cleaned_channel
        song.url = cleaned_url
        song.lyrics = lyrics
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
        
        # History DBの変更内容とDisocrdの#新規作成・変更チャンネルに送る文の用意
        changes = [["種類", "編集前", "編集後"]]
        changed_labels = []
        discord_text = f"編集されました\n{ROOT_URL}/songs/{song_id}/history\n\n"
        for column in COLUMNS:
            if column["before"] != column["after"]:     # ユーザーが編集時に変更した場合
                label = column["label"]
                changed_labels.append(label)

                before = column.get("before", "なし")
                after = column.get("after", "なし")

                # 共通：Markdownテーブル
                changes.append([label, before, after])

                # Discord用テキスト
                discord_text += f"**{label}**："
                if label == "歌詞":
                    discord_text += f"```{after}```\n"
                elif label == "模倣":
                    discord_text += f"\n{before} \n:arrow_down: \n{after}\n"
                else:
                    # beforeが存在する場合追記する
                    if len(before) != 0:
                        discord_text += f"`{before}` :arrow_right: "
                    discord_text += f"`{after}`\n"
                
        title = f"{title}の{'と'.join(changed_labels)}を編集"
        
        if len(changed_labels) >= 1:
            # 編集履歴を保存
            editor, _ = Editor.objects.get_or_create(ip = ip)
            history = History(
                song = song,
                title = title,
                history_type = "new",
                create_time = timezone.now(),
                temp_changes = changes,
                editor = editor
            )
            history.save()
            
            discord_text += f"編集者：`{editor}`"
            
            # Discordに送信し、送信できなければ削除し500ページに遷移
            is_ok = send_discord(NEW_DISCORD_URL, discord_text)
            if not is_ok:
                return render(request, 'subekashi/500.html', status=500)
        
        response = redirect(f'/songs/{song_id}?toast=edit')
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
    return render(request, 'subekashi/song_edit.html', dataD)
