from django.shortcuts import render, redirect
from django.utils import timezone
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.youtube import *
from subekashi.lib.song_filter import song_filter


def song_new(request):
    dataD = {
        "metatitle": "曲の登録",
    }

    if request.method == "POST":
        title = request.POST.get("title", "")
        channel = request.POST.get("channel", "")
        url = request.POST.get("url", "")
        is_original = bool(request.POST.get("is-original-auto", "") + request.POST.get("is-original-manual", ""))
        is_deleted = bool(request.POST.get("is-deleted-auto", "") + request.POST.get("is-deleted-manual", ""))
        is_joke = bool(request.POST.get("is-joke-auto", "") + request.POST.get("is-joke-manual", ""))
        is_inst = bool(request.POST.get("is-inst-auto", "") + request.POST.get("is-inst-manual", ""))
        is_subeana = bool(request.POST.get("is-subeana-auto", "") + request.POST.get("is-subeana-manual", ""))
        
        # YouTube APIから情報取得
        youtube_res = {}
        if is_youtube_url(url) :
            youtube_id = get_youtube_id(url)
            youtube_res = get_youtube_api(youtube_id)
            title = youtube_res.get("title", "")
            channel = youtube_res.get("channel", "")
            
        # URLがYouTubeのURLでない場合はエラー
        if not is_youtube_url(url) and url:
            dataD["error"] = "URLがYouTubeのURLではありません。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        # URLが複数ならエラー
        if "," in url:
            dataD["error"] = "URLは複数入力できません。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        # 既に登録されているURLの場合はエラー
        cleaned_url = clean_url(url)
        song_qs, _ = song_filter({"url": cleaned_url})
        if song_qs.exists() and url:
            dataD["error"] = "URLは既に登録されています。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        # タイトルかチャンネルが空の場合はエラー
        if ("" in [title, channel]) :
            dataD["error"] = "タイトルかチャンネルが空です。"
            return render(request, 'subekashi/song_new.html', dataD)

        # チャンネル(作者)が空白のみの場合はエラー
        if title.strip() == "" or channel.strip() == "":
            dataD["error"] = "作者は空白にできません。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        # DBに保存する値たち
        # TODO Channelテーブルを利用する
        # WARNING channelはそのままURLになるので/は別の文字╱に変換しないといけない
        cleaned_channel = channel.replace("/", "╱").replace(" ,", ",").replace(", ", ",")
        
        # フォームに書かれた各チャンネルの掲載拒否
        try:
            from subekashi.constants.dynamic.reject import REJECT_LIST
        except:
            REJECT_LIST = []
        
        for check_channel in cleaned_channel.split(","):
            if check_channel in REJECT_LIST:
                dataD["error"] = f"{check_channel}さんの曲は登録することができません。"
                return render(request, 'subekashi/song_new.html', dataD)
        
        # Songの登録
        ip = get_ip(request)
        song = Song(
            title = title,
            channel = cleaned_channel,
            url = cleaned_url,
            post_time = timezone.now(),
            isoriginal = is_original,
            isdeleted = is_deleted,
            isjoke = is_joke,
            isinst = is_inst,
            issubeana = is_subeana,
            upload_time = youtube_res.get("upload_time", None),
            view = youtube_res.get("view", None),
            like = youtube_res.get("like", None),
        )
        
        song.save()
        song_id = song.id
        
        # 変更内容のマークダウンと送信するDiscordの文言の作成
        def yes_no(value):
            return "はい" if value else "いいえ"
        
        COLUMNS = [
            {"label": "タイトル", "value": title},
            {"label": "チャンネル名", "value": cleaned_channel},
            {"label": "URL", "value": cleaned_url},
            {"label": "オリジナル", "value": yes_no(is_original)},
            {"label": "削除済み", "value": yes_no(is_deleted)},
            {"label": "ネタ曲", "value": yes_no(is_joke)},
            {"label": "インスト曲", "value": yes_no(is_inst)},
            {"label": "すべあな模倣曲", "value": yes_no(is_subeana)},
        ]
        
        changes = [["種類", "内容"]]
        discord_text = f"新規作成されました\n{ROOT_URL}/songs/{song_id}\n\n"
        for column in COLUMNS:
            if column["value"]:     # 通常、manual送信時にlabel=URLだけがFalseになる
                changes.append([column['label'], column['value']])
                discord_text += f"**{column['label']}**：`{column['value']}`\n"

        # 編集履歴を保存
        editor, _ = Editor.objects.get_or_create(ip = ip)
        history = History(
            song = song,
            title = f"{song.title}を新規作成",
            history_type = "new",
            create_time = timezone.now(),
            changes = changes,
            editor = editor
        )
        history.save()
        
        discord_text += f"編集者：`{editor}`"
        # Discordに送信し、送信できなければ削除し500ページに遷移
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            song.delete()
            return render(request, 'subekashi/500.html', status=500)
        
        # 登録できましたトーストを表示する
        return redirect(f'/songs/{song_id}/edit?toast={request.GET.get("toast")}')
    return render(request, 'subekashi/song_new.html', dataD)