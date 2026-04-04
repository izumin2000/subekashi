from django.shortcuts import render, redirect
from config.local_settings import CONTACT_DISCORD_URL, NEW_DISCORD_URL
from subekashi.models import Editor, History, SongLink, SongFields
from subekashi.lib.url import clean_url, get_allow_media, is_youtube_url, get_youtube_id
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.youtube import get_youtube_api
from subekashi.lib.author_helpers import get_or_create_authors
from subekashi.lib.song_service import (
    check_reject_list,
    validate_song_url,
    create_song_with_relations,
    build_new_song_discord_text,
)


def song_new(request):
    dataD = {
        "metatitle": "曲の登録",
    }

    if request.method == "POST":
        title = request.POST.get("title", "")
        authors_input = request.POST.get("authors", "")
        url = request.POST.get("url", "")
        is_original = bool(request.POST.get("is-original-auto", "") + request.POST.get("is-original-manual", ""))
        is_deleted = bool(request.POST.get("is-deleted-auto", "") + request.POST.get("is-deleted-manual", ""))
        is_joke = bool(request.POST.get("is-joke-auto", "") + request.POST.get("is-joke-manual", ""))
        is_inst = bool(request.POST.get("is-inst-auto", "") + request.POST.get("is-inst-manual", ""))
        is_subeana = bool(request.POST.get("is-subeana-auto", "") + request.POST.get("is-subeana-manual", ""))

        # YouTube APIから情報取得
        youtube_res = {}
        if is_youtube_url(url):
            youtube_id = get_youtube_id(url)
            youtube_res = get_youtube_api(youtube_id)
            title = youtube_res.get("title", "")
            authors_input = youtube_res.get("author", "")       # 現状、YouTube Data APIの仕様上,1チャンネルしか取得できない。

        # URLがYouTubeのURLでない場合はエラー
        if not is_youtube_url(url) and url:
            dataD["error"] = "URLがYouTubeのURLではありません。"
            return render(request, 'subekashi/song_new.html', dataD)

        # URLが複数ならエラー
        if "," in url:
            dataD["error"] = "URLは複数入力できません。"
            return render(request, 'subekashi/song_new.html', dataD)

        # 既に登録されているURLの場合はエラー（allow_dup=Falseのみ）
        cleaned_url = clean_url(url)
        if cleaned_url:
            error = validate_song_url(cleaned_url)
            if error:
                dataD["error"] = error
                return render(request, 'subekashi/song_new.html', dataD)

        # 作者が空または空白のみの場合はエラー
        if not authors_input.strip():
            dataD["error"] = "作者は空白にできません。"
            return render(request, 'subekashi/song_new.html', dataD)

        # タイトルが空の場合はエラー
        if not title:
            dataD["error"] = "タイトルが未入力です。"
            return render(request, 'subekashi/song_new.html', dataD)

        cleaned_authors = authors_input.replace(" ,", ",").replace(", ", ",")

        # authorsフィールドの処理: カンマ区切りの作者名をAuthorオブジェクトに変換
        author_names = cleaned_authors.split(',')
        authors = get_or_create_authors(author_names)

        # 掲載拒否作者か判断する
        reject_error = check_reject_list(authors)
        if reject_error:
            dataD["error"] = reject_error
            return render(request, 'subekashi/song_new.html', dataD)

        # Songの登録
        ip = get_ip(request)
        fields = SongFields(
            title=title,
            is_original=is_original,
            is_deleted=is_deleted,
            is_joke=is_joke,
            is_inst=is_inst,
            is_subeana=is_subeana,
            upload_time=youtube_res.get("upload_time", None),
            view=youtube_res.get("view", None),
            like=youtube_res.get("like", None),
        )
        song = create_song_with_relations(fields, authors, cleaned_url)
        song_id = song.id

        # Discordテキストとchangesを構築
        editor = Editor.get_or_create_from_ip(ip)
        changes, discord_text = build_new_song_discord_text(song_id, fields, authors, cleaned_url, editor)

        # Discordに送信し、送信できなければ削除し500ページに遷移
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            song.delete()
            return render(request, 'subekashi/500.html', status=500)

        # 編集履歴を保存
        History.create_for_song(
            song=song,
            title=f"{song.title}を新規作成",
            history_type="new",
            changes=changes,
            editor=editor,
        )

        # 登録できましたトーストを表示する
        return redirect(f'/songs/{song_id}/edit?toast={request.GET.get("toast")}')
    allow_dup_url = request.GET.get('allow_dup_url', '')
    if allow_dup_url:
        cleaned = clean_url(allow_dup_url) or allow_dup_url
        link = SongLink.set_allow_dup_for_url(cleaned)
        if link:
            send_discord(CONTACT_DISCORD_URL, f"重複許可したURL：{allow_dup_url}")
    return render(request, 'subekashi/song_new.html', dataD)
