from django.shortcuts import render, redirect
from django.urls import reverse
from config.local_settings import NEW_DISCORD_URL, CONTACT_DISCORD_URL
from subekashi.models import Song, Editor, History, SongLink, SongFields
from subekashi.lib.url import clean_url, get_allow_media
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.author_helpers import get_or_create_authors
from subekashi.lib.song_service import (
    check_reject_list,
    validate_song_url,
    get_imitate_songs,
    update_song,
    build_edit_song_discord_text,
)


def song_edit(request, song_id):
    # Songがなければ404
    song = Song.get_or_none(song_id)
    if song is None:
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
            error = validate_song_url(cleaned_url_item, exclude_song_id=song_id)
            if error:
                dataD["error"] = error
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
        imitate_songs = get_imitate_songs(imitates, song_id)

        # 掲載拒否作者か判断する
        reject_error = check_reject_list(author_objects)
        if reject_error:
            dataD["error"] = reject_error
            return render(request, 'subekashi/song_edit.html', dataD)

        fields = SongFields(
            title=title,
            lyrics=lyrics,
            is_original=is_original,
            is_deleted=is_deleted,
            is_joke=is_joke,
            is_inst=is_inst,
            is_subeana=is_subeana,
            is_draft=is_draft,
        )

        # Discordテキストとchangesを構築（song更新前に実行）
        editor = Editor.get_or_create_from_ip(ip)
        edit_title, changes, discord_text, changed_labels = build_edit_song_discord_text(
            song_id, song, fields, author_objects, cleaned_url, imitate_songs, editor,
        )

        # songの更新
        update_song(song, fields, author_objects, imitate_songs, cleaned_url_list)

        if changed_labels:
            # 編集履歴を保存
            History.create_for_song(
                song=song,
                title=edit_title,
                history_type="edit",
                changes=changes,
                editor=editor,
            )

            # Discordに送信し、送信できなければ500ページに遷移
            is_ok = send_discord(NEW_DISCORD_URL, discord_text)
            if not is_ok:
                return render(request, 'subekashi/500.html', status=500)

        response = redirect(f'/songs/{song_id}?toast=edit')
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
    allow_dup_url = request.GET.get('allow_dup_url', '')
    if allow_dup_url:
        cleaned = clean_url(allow_dup_url) or allow_dup_url
        link = SongLink.set_allow_dup_for_url(cleaned)
        if link:
            send_discord(CONTACT_DISCORD_URL, f"重複許可したURL：{allow_dup_url}")
    return render(request, 'subekashi/song_edit.html', dataD)
