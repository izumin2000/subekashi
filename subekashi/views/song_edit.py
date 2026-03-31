from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse
from config.local_settings import NEW_DISCORD_URL, CONTACT_DISCORD_URL
from config.settings import ROOT_URL
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.song_search import song_search
from subekashi.lib.author_helpers import get_or_create_authors


def song_edit(request, song_id):
    # Songがなければ404
    try :
        song = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    # 編集不可の場合は元の曲情報閲覧画面に戻してロックされていますトーストを表示
    if song.is_lock:
        return redirect(f'/songs/{song_id}?toast=lock')
    
    dataD = {
        "metatitle": f"{song.title}の編集",
        "song": song,
    }

    if request.method == "POST":
        title = request.POST.get("title", "")
        authors_input = request.POST.get("authors", "")
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
            # allow_dup=Falseかつ自身以外の曲に紐づくURLが既に存在する場合はエラー
            if SongLink.objects.filter(url__iexact=cleaned_url_item, allow_dup=False).exclude(songs__id=song_id).filter(songs__isnull=False).exists():
                dataD["error"] = "URLは既に登録されています。"
                return render(request, 'subekashi/song_edit.html', dataD)
            
            # 許可されていないメディアのURLならばエラー
            if not get_allow_media(cleaned_url_item):
                contact_url = reverse('subekashi:contact')
                dataD["error"] = f"URL：{cleaned_url_item}は信頼されていないURLと判断されました。<br>\
                <a href='{contact_url}?&category=提案&detail={cleaned_url_item} を登録できるようにしてください。' target='_blank'>お問い合わせ</a>にて、\
                該当のURLを登録できるように、ご連絡ください。"
                return render(request, 'subekashi/song_edit.html', dataD)

        # 作者が空または空白のみの場合はエラー
        if not authors_input.strip():
            dataD["error"] = "作者は空白にできません。"
            return render(request, 'subekashi/song_edit.html', dataD)

        # タイトルが空の場合はエラー
        if not title:
            dataD["error"] = "タイトルが未入力です。"
            return render(request, 'subekashi/song_edit.html', dataD)

        # DBに保存する値たち
        ip = get_ip(request)
        cleaned_authors = authors_input.replace(" ,", ",").replace(", ", ",")

        # authorsフィールドの処理: カンマ区切りの作者をAuthorオブジェクトに変換
        author_names = cleaned_authors.split(',')
        author_objects = get_or_create_authors(author_names)
        
        # 自分自身や重複は除外し、Song オブジェクトのリストに変換
        imitate_ids = set()
        for i in imitates.split(","):
            i = i.strip()
            if i and i != str(song_id):
                try:
                    imitate_ids.add(int(i))
                except ValueError:
                    pass
        imitate_songs = list(Song.objects.filter(id__in=imitate_ids))
        
        # 掲載拒否リストの読み込み
        try:
            from subekashi.constants.dynamic.reject import REJECT_LIST
        except:
            REJECT_LIST = []
        
        # 掲載拒否作者か判断する
        for author in author_objects:
            if author.name in REJECT_LIST:
                dataD["error"] = f"{author.name}さんの曲は登録することができません。"
                return render(request, 'subekashi/song_edit.html', dataD)

        # 模倣の編集（ManyToManyはsetで差分を自動管理）
        old_imitate_songs = list(song.imitates.all())
        
        # 変更内容のマークダウンと送信するDiscordの文言の作成
        def yes_no(value):
            return "はい" if value else "いいえ"

        # Songのリストをタイトルの改行リストにする
        def songs_to_info(songs):
            return "\n".join(s.title for s in songs)

        # URL変更前後の値を取得（SongLinkベース）
        before_urls = ",".join(song.links.order_by('id').values_list('url', flat=True))

        # songを更新する前にhistoryのために更新前後のsongの情報を記録しておく
        COLUMNS = [
            {"label": "タイトル", "before": song.title ,"after": title},
            {"label": "作者", "before": song.authors_str(), "after": ", ".join([a.name for a in author_objects])},
            {"label": "URL", "before": before_urls ,"after": cleaned_url},
            {"label": "オリジナル", "before": yes_no(song.is_original) ,"after": yes_no(is_original)},
            {"label": "削除済み", "before": yes_no(song.is_deleted) ,"after": yes_no(is_deleted)},
            {"label": "ネタ曲", "before": yes_no(song.is_joke) ,"after": yes_no(is_joke)},
            {"label": "インスト曲", "before": yes_no(song.is_inst) ,"after": yes_no(is_inst)},
            {"label": "すべあな模倣曲", "before": yes_no(song.is_subeana) ,"after": yes_no(is_subeana)},
            {"label": "下書き", "before": yes_no(song.is_draft) ,"after": yes_no(is_draft)},
            {"label": "模倣", "before": songs_to_info(old_imitate_songs), "after": songs_to_info(imitate_songs)},
            {"label": "歌詞", "before": song.lyrics, "after": lyrics.replace("\r\n", "\n")},
        ]

        # songの更新
        song.title = title
        song.lyrics = lyrics
        song.is_original = is_original
        song.is_deleted = is_deleted
        song.is_joke = is_joke
        song.is_inst = is_inst
        song.is_subeana = is_subeana
        song.is_draft = is_draft
        song.post_time = timezone.now()
        with transaction.atomic():
            song.save()
            song.imitates.set(imitate_songs)
            song.authors.set(author_objects)

            # SongLinkの更新（差分）
            existing_links = {link.url: link for link in song.links.all()}
            new_url_set = set(cleaned_url_list)
            # 削除されたURLのSongLinkからこの曲を外す（他の曲が参照していなければ削除）
            for url_str, link in existing_links.items():
                if url_str not in new_url_set:
                    link.songs.remove(song)
                    if not link.songs.exists():
                        link.delete()
            # 新規追加されたURLはSongLinkを取得または作成してこの曲を追加
            for url_str in new_url_set:
                if url_str not in existing_links:
                    link, _ = SongLink.objects.get_or_create(url=url_str)
                    link.songs.add(song)

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
                changes = changes,
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
    allow_dup_url = request.GET.get('allow_dup_url', '')
    if allow_dup_url:
        cleaned = clean_url(allow_dup_url) or allow_dup_url
        link = SongLink.objects.filter(url__iexact=cleaned).first()
        if link:
            link.allow_dup = True
            link.save()
            send_discord(CONTACT_DISCORD_URL, f"重複許可したURL：{allow_dup_url}")
    return render(request, 'subekashi/song_edit.html', dataD)
