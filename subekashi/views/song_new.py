from django.shortcuts import render, redirect
from django.db import transaction
from django.views import View
from config.local_settings import CONTACT_DISCORD_URL, NEW_DISCORD_URL
from subekashi.constants.constants import SONG_CATEGORIES
from subekashi.models import Editor, History, Song, SongFields
from subekashi.lib.url import clean_url, is_youtube_url, get_youtube_id
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.youtube import get_youtube_api, YoutubeApiError
from subekashi.lib.author_helpers import get_or_create_authors, author_names_were_normalized, validate_author_name_lengths
from subekashi.lib.song_service import (
    check_reject_list,
    validate_song_url,
    allow_song_url_dup,
    create_song_with_relations,
    build_new_song_discord_text,
    build_allow_dup_discord_text,
)


class SongNewView(View):
    def get_base_context(self):
        return {"metatitle": "曲の登録", "SONG_CATEGORIES": SONG_CATEGORIES}

    def get(self, request):
        return render(request, 'subekashi/song_new.html', self.get_base_context())

    def post(self, request):
        context = self.get_base_context()
        title = request.POST.get("title", "")
        authors_input = request.POST.get("authors", "")
        url = request.POST.get("url", "")
        is_original = bool(request.POST.get("is-original-auto", "") + request.POST.get("is-original-manual", ""))
        is_deleted = bool(request.POST.get("is-deleted-auto", "") + request.POST.get("is-deleted-manual", ""))
        is_joke = bool(request.POST.get("is-joke-auto", "") + request.POST.get("is-joke-manual", ""))
        is_inst = bool(request.POST.get("is-inst-auto", "") + request.POST.get("is-inst-manual", ""))
        is_subeana = bool(request.POST.get("is-subeana-auto", "") + request.POST.get("is-subeana-manual", ""))
        is_questionable = bool(request.POST.get("is-questionable-auto", "") + request.POST.get("is-questionable-manual", ""))
        category = request.POST.get("category") or "song"

        # is_questionableの場合、オリジナル模倣はユーザーの入力値に関わらず空にする
        if is_questionable:
            is_original = False

        # カテゴリが選択肢にない場合はエラー
        if category not in dict(Song.CHOICES):
            context["error"] = "カテゴリが不正です。"
            return render(request, 'subekashi/song_new.html', context)

        # URLがYouTubeのURLでない場合はエラー
        if not is_youtube_url(url) and url:
            context["error"] = "URLがYouTubeのURLではありません。"
            return render(request, 'subekashi/song_new.html', context)

        # URLが複数ならエラー
        if "," in url:
            context["error"] = "URLは複数入力できません。"
            return render(request, 'subekashi/song_new.html', context)

        # 既に登録されているURLの場合はエラー（allow_dup=Falseのみ）
        # 重複を許可して登録する場合は、曲を保存するときに重複を許可する（#1285）
        cleaned_url = clean_url(url)
        allow_dup = bool(cleaned_url) and clean_url(request.POST.get("allow_dup_url", "")) == cleaned_url
        if cleaned_url:
            error = validate_song_url(cleaned_url, allow_dup=allow_dup)
            if error:
                context["error"] = error
                return render(request, 'subekashi/song_new.html', context)

        # YouTube APIから情報取得
        youtube_res = {}
        if is_youtube_url(url):
            youtube_id = get_youtube_id(url)
            # インターネットに接続できなかった場合なども含め、呼び出しに失敗した場合は動画が削除・非公開であるとは限らない
            try:
                youtube_res = get_youtube_api(youtube_id)
            except YoutubeApiError:
                context["error"] = "インターネットに接続できなかったなどの理由で、YouTubeから動画の情報を取得できませんでした。時間をおいて再度お試しいただくか、タイトルと作者から登録してください。"
                return render(request, 'subekashi/song_new.html', context)

            # 動画が削除・非公開の場合は、タイトルと作者から登録するよう案内する
            if not youtube_res:
                context["error"] = "この動画はYouTube上で削除されたか非公開になっているため、タイトルと作者を取得できませんでした。「タイトルと作者から登録」で「非公開/削除済み」にチェックを入れて登録してください。URLは登録後に編集画面で追加できます。"
                return render(request, 'subekashi/song_new.html', context)

            title = youtube_res.get("title", "")
            authors_input = youtube_res.get("author", "")       # 現状、YouTube Data APIの仕様上,1チャンネルしか取得できない。

        # 作者が空または空白のみの場合はエラー
        if not authors_input.strip():
            context["error"] = "作者は空白にできません。"
            return render(request, 'subekashi/song_new.html', context)

        # タイトルが空の場合はエラー
        if not title:
            context["error"] = "タイトルが未入力です。"
            return render(request, 'subekashi/song_new.html', context)

        # タイトルが長すぎる場合はエラー
        title_max_length = Song._meta.get_field('title').max_length
        if len(title) > title_max_length:
            context["error"] = f"タイトルは{title_max_length}文字以下である必要があります。"
            return render(request, 'subekashi/song_new.html', context)

        cleaned_authors = authors_input.replace(" ,", ",").replace(", ", ",")

        # authorsフィールドの処理: カンマ区切りの作者名をAuthorオブジェクトに変換
        author_names = cleaned_authors.split(',')

        # 作者名が長すぎる場合はエラー
        author_name_error = validate_author_name_lengths(author_names)
        if author_name_error:
            context["error"] = author_name_error
            return render(request, 'subekashi/song_new.html', context)

        authors = get_or_create_authors(author_names)
        # 入力した作者名が統一した名義（past別名から変換）に正規化されたかどうか
        name_unified = author_names_were_normalized(author_names, authors)

        # 掲載拒否作者か判断する
        reject_error = check_reject_list(authors)
        if reject_error:
            context["error"] = reject_error
            return render(request, 'subekashi/song_new.html', context)

        # Songの登録
        ip = get_ip(request)
        fields = SongFields(
            title=title,
            is_original=is_original,
            is_deleted=is_deleted,
            is_joke=is_joke,
            is_inst=is_inst,
            is_subeana=is_subeana,
            is_questionable=is_questionable,
            category=category,
            upload_time=youtube_res.get("upload_time", None),
            view=youtube_res.get("view", None),
            like=youtube_res.get("like", None),
        )
        # URLの重複の許可・Song・Editor・Historyをトランザクションでまとめて保存し、
        # 全て成功した場合のみDiscordに送信する
        with transaction.atomic():
            # 新しい曲を紐づける前に許可し、そのURLを元から持つ曲の編集履歴に残す
            dup_link = allow_song_url_dup(cleaned_url, ip) if allow_dup else None
            song = create_song_with_relations(fields, authors, cleaned_url)
            song_id = song.id
            editor = Editor.get_or_create_from_ip(ip)
            changes, discord_text = build_new_song_discord_text(song_id, fields, authors, cleaned_url, editor)
            History.create_for_song(
                song=song,
                title=f"{song.title}を新規作成",
                history_type="new",
                changes=changes,
                editor=editor,
            )

        if dup_link:
            send_discord(CONTACT_DISCORD_URL, build_allow_dup_discord_text(dup_link, ip))

        # Discordに送信し、送信できなければ削除し500ページに遷移
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            song.delete()
            return render(request, 'subekashi/500.html', status=500)

        # 登録できましたトーストを表示する
        redirect_url = f'/songs/{song_id}/edit?toast={request.GET.get("toast")}'
        if name_unified:
            redirect_url += '&name_unified=1'
        return redirect(redirect_url)
