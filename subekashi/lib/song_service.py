from config.settings import ROOT_URL


def check_reject_list(authors):
    """掲載拒否リストをチェック。NGならエラーメッセージを返す。問題なければNone。"""
    try:
        from subekashi.constants.dynamic.reject import REJECT_LIST
    except Exception:
        REJECT_LIST = []
    for author in authors:
        if author.name in REJECT_LIST:
            return f"{author.name}さんの曲は登録することができません。"
    return None


def yes_no(value):
    return "はい" if value else "いいえ"


def validate_song_url(cleaned_url, exclude_song_id=None):
    """URLの重複チェック。エラーメッセージを返す。問題なければNone。"""
    from subekashi.models import SongLink
    qs = SongLink.objects.filter(url__iexact=cleaned_url, allow_dup=False, songs__isnull=False)
    if exclude_song_id is not None:
        qs = qs.exclude(songs__id=exclude_song_id)
    if qs.exists():
        return "URLは既に登録されています。"
    return None


def create_song(title, is_original, is_deleted, is_joke, is_inst, is_subeana,
                upload_time=None, view=None, like=None):
    """Songを作成して保存する"""
    from django.utils import timezone
    from subekashi.models import Song
    song = Song(
        title=title,
        post_time=timezone.now(),
        is_original=is_original,
        is_deleted=is_deleted,
        is_joke=is_joke,
        is_inst=is_inst,
        is_subeana=is_subeana,
        upload_time=upload_time,
        view=view,
        like=like,
    )
    song.save()
    return song


def set_song_authors_and_links(song, authors, cleaned_url):
    """Songのauthorsと SongLink を設定する"""
    from subekashi.models import SongLink
    song.authors.set(authors)
    for url_str in (cleaned_url.split(",") if cleaned_url else []):
        link, _ = SongLink.objects.get_or_create(url=url_str)
        link.songs.add(song)


def get_imitate_songs(imitates_str, self_id):
    """カンマ区切りの模倣曲IDリストをSongオブジェクトのリストに変換する"""
    from subekashi.models import Song
    imitate_ids = set()
    for i in imitates_str.split(","):
        i = i.strip()
        if i and i != str(self_id):
            try:
                imitate_ids.add(int(i))
            except ValueError:
                pass
    return list(Song.objects.filter(id__in=imitate_ids))


def update_song(song, title, lyrics, is_original, is_deleted, is_joke, is_inst,
                is_subeana, is_draft, author_objects, imitate_songs, cleaned_url_list):
    """Songを更新し、関連するauthors/imitates/SongLinkも差分更新する（トランザクション）"""
    from django.utils import timezone
    from django.db import transaction
    from subekashi.models import SongLink
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
        existing_links = {link.url: link for link in song.links.all()}
        new_url_set = set(cleaned_url_list)
        for url_str, link in existing_links.items():
            if url_str not in new_url_set:
                link.songs.remove(song)
                if not link.songs.exists():
                    link.delete()
        for url_str in new_url_set:
            if url_str not in existing_links:
                link, _ = SongLink.objects.get_or_create(url=url_str)
                link.songs.add(song)


def build_delete_discord_text(song, reason, editor):
    """削除申請用のDiscordテキストを構築する"""
    return (
        f"```{song.id}```\n"
        f"{ROOT_URL}/songs/{song.id}\n"
        f"タイトル：{song.title}\n"
        f"チャンネル名：{song.authors_str()}\n"
        f"理由：{reason}\n"
        f"編集者：{editor}"
    )


def get_song_links_with_media(song):
    """SongのURLリストをメディア情報付きのdictリストで返す"""
    from subekashi.lib.url import get_all_media
    links = []
    for link in song.links.all():
        media = get_all_media(link.url)
        links.append({
            "text": link.url,
            "icon": media["icon"],
            "name": media["name"],
        })
    return links


def build_new_song_discord_text(song_id, title, authors, cleaned_url,
                                 is_original, is_deleted, is_joke, is_inst, is_subeana,
                                 editor):
    """新規作成用のchangesリストとDiscordテキストを構築する"""
    COLUMNS = [
        {"label": "タイトル", "value": title},
        {"label": "作者", "value": ", ".join([a.name for a in authors])},
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
        if column["value"]:
            changes.append([column["label"], column["value"]])
            discord_text += f"**{column['label']}**：`{column['value']}`\n"

    discord_text += f"編集者：`{editor}`"
    return changes, discord_text


def get_top_news_articles():
    """トップページ用のニュース・リリース記事を返す"""
    from django.db.models import Q
    from article.models import Article
    return Article.objects.filter(
        is_open=True
    ).filter(
        Q(tag="news") | Q(tag="release")
    ).order_by("-post_time")[:3]


def build_edit_song_discord_text(song_id, song, title, author_objects, cleaned_url,
                                  imitate_songs,
                                  lyrics, is_original, is_deleted, is_joke, is_inst,
                                  is_subeana, is_draft, editor):
    """編集用のchangesリスト・Discordテキスト・変更ラベルリストを構築する"""
    def songs_to_info(songs):
        return "\n".join(s.title for s in songs)

    old_imitate_songs = list(song.imitates.all())
    before_urls = ",".join(song.links.order_by('id').values_list('url', flat=True))

    COLUMNS = [
        {"label": "タイトル", "before": song.title, "after": title},
        {"label": "作者", "before": song.authors_str(), "after": ", ".join([a.name for a in author_objects])},
        {"label": "URL", "before": before_urls, "after": cleaned_url},
        {"label": "オリジナル", "before": yes_no(song.is_original), "after": yes_no(is_original)},
        {"label": "削除済み", "before": yes_no(song.is_deleted), "after": yes_no(is_deleted)},
        {"label": "ネタ曲", "before": yes_no(song.is_joke), "after": yes_no(is_joke)},
        {"label": "インスト曲", "before": yes_no(song.is_inst), "after": yes_no(is_inst)},
        {"label": "すべあな模倣曲", "before": yes_no(song.is_subeana), "after": yes_no(is_subeana)},
        {"label": "下書き", "before": yes_no(song.is_draft), "after": yes_no(is_draft)},
        {"label": "模倣", "before": songs_to_info(old_imitate_songs), "after": songs_to_info(imitate_songs)},
        {"label": "歌詞", "before": song.lyrics, "after": lyrics.replace("\r\n", "\n")},
    ]

    changes = [["種類", "編集前", "編集後"]]
    changed_labels = []
    discord_text = f"編集されました\n{ROOT_URL}/songs/{song_id}/history\n\n"

    for column in COLUMNS:
        if column["before"] != column["after"]:
            label = column["label"]
            changed_labels.append(label)
            before = column.get("before", "なし")
            after = column.get("after", "なし")
            changes.append([label, before, after])
            discord_text += f"**{label}**："
            if label == "歌詞":
                discord_text += f"```{after}```\n"
            elif label == "模倣":
                discord_text += f"\n{before} \n:arrow_down: \n{after}\n"
            else:
                if len(before) != 0:
                    discord_text += f"`{before}` :arrow_right: "
                discord_text += f"`{after}`\n"

    edit_title = f"{title}の{'と'.join(changed_labels)}を編集"

    if changed_labels:
        discord_text += f"編集者：`{editor}`"

    return edit_title, changes, discord_text, changed_labels
