import re
import string
from django.utils import timezone
from django.db import transaction
from config.settings import ROOT_URL
from subekashi.constants.constants import SONG_CATEGORIES
from subekashi.models import Song, SongLink, SongFields, Editor, History
from subekashi.lib.author_helpers import get_same_person_author_ids
from subekashi.lib.url import get_all_media
from subekashi.lib.embed import get_embed


# short版のタイトルに付く「short」の部分（#667）
# shortを含む括弧（例：[short]・(Short Ver.)・【very short】）か、括弧がなければ区切り文字を含むshortの語（例：「 - short」「.short」）
SHORT_TOKEN_REGEX = re.compile(
    r"[\[(（【［{][^\[\]()（）【】［］{}]*?short[^\[\]()（）【】［］{}]*?[\])）】］}]|[\s.\-_/]*short",
    re.IGNORECASE,
)

# full版のタイトルの末尾に付く「full」の部分（#667）
# fullで始まる括弧（例：[full]・（Full）・(Full ver.)）か、英字の直後ではないfullの語（例：「死んだらしいfull」「　FULLスギ」）
FULL_TOKEN_REGEX = re.compile(
    r"\s*(?:[\[(（【［{]\s*full[^\[\]()（）【】［］{}]*[\])）】］}]|(?<![a-z])full\S*)\s*$",
    re.IGNORECASE,
)

# full版・short版のタイトルの比較では、英字の大文字小文字のみ区別しない（#667）
# 「Λ」と「λ」のように記号として使われる文字は別のタイトルとして扱う
ASCII_LOWERCASE_TABLE = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def check_reject_list(authors):
    """掲載拒否リストをチェック。NGならエラーメッセージを返す。問題なければNone。"""
    try:
        from subekashi.constants.dynamic.reject import REJECT_LIST
    except ImportError:
        REJECT_LIST = []
    for author in authors:
        if author.name in REJECT_LIST:
            return f"{author.name}さんの曲は登録することができません。"
    return None


def yes_no(value):
    return "はい" if value else "いいえ"


def category_label(category):
    return dict(Song.CHOICES).get(category, category)


def validate_song_url(cleaned_url, exclude_song_id=None):
    """URLの長さ・重複チェック。エラーメッセージを返す。問題なければNone。"""
    max_length = SongLink._meta.get_field('url').max_length
    if len(cleaned_url) > max_length:
        return f"URLは{max_length}文字以下である必要があります。"

    # 削除した曲（#1239）だけに紐づくURLは、登録されていないURLとして扱う
    qs = SongLink.objects.filter(url__iexact=cleaned_url, allow_dup=False, songs__is_removed=False)
    if exclude_song_id is not None:
        qs = qs.exclude(songs__id=exclude_song_id)
    if qs.exists():
        return "URLは既に登録されています。"
    return None


def allow_song_url_dup(url, ip):
    """URLの重複を許可し、そのURLを元から持つ曲の編集履歴に残す（#1282）。SongLinkが無ければNoneを返す

    既に重複を許可しているURLは、ページを再読み込みしても履歴が増えないよう、履歴を残さない。
    同時に呼ばれても履歴が二重にならないよう、allow_dup=Falseの行を更新できたときだけ履歴を残す。
    """
    with transaction.atomic():
        link = SongLink.objects.filter(url__iexact=url).first()
        if link is None:
            return None
        if SongLink.objects.filter(pk=link.pk, allow_dup=False).update(allow_dup=True):
            link.allow_dup = True
            editor = Editor.get_or_create_from_ip(ip)
            for song in link.songs.all():
                History.create_for_song(
                    song=song,
                    title=f"{song.title}のURLの重複を許可",
                    history_type="edit",
                    changes=[["種類", "内容"], ["重複許可したURL", link.url]],
                    editor=editor,
                )
    return link


def create_song(fields: SongFields):
    """Songを作成して保存する"""
    song = Song(
        title=fields.title,
        post_time=timezone.now(),
        is_original=fields.is_original,
        is_deleted=fields.is_deleted,
        is_joke=fields.is_joke,
        is_inst=fields.is_inst,
        is_subeana=fields.is_subeana,
        is_questionable=fields.is_questionable,
        category=fields.category,
        upload_time=fields.upload_time,
        view=fields.view,
        like=fields.like,
    )
    song.save()
    return song


def set_song_authors_and_links(song, authors, cleaned_url):
    """Songのauthorsと SongLink を設定する"""
    song.authors.set(authors)
    for url_str in (cleaned_url.split(",") if cleaned_url else []):
        link, _ = SongLink.objects.get_or_create(url=url_str)
        link.songs.add(song)


def create_song_with_relations(fields: SongFields, authors, cleaned_url):
    """Songとauthors/SongLinkをトランザクションでまとめて作成する"""
    with transaction.atomic():
        song = create_song(fields)
        set_song_authors_and_links(song, authors, cleaned_url)
    return song


def get_imitate_songs(imitates_str, self_id):
    """カンマ区切りの模倣曲IDリストをSongオブジェクトのリストに変換する"""
    imitate_ids = set()
    for i in imitates_str.split(","):
        i = i.strip()
        if i and i != str(self_id):
            try:
                imitate_ids.add(int(i))
            except ValueError:
                pass
    return list(Song.objects.filter(id__in=imitate_ids))


def update_song(song, fields: SongFields, author_objects, imitate_songs, cleaned_url_list):
    """Songを更新し、関連するauthors/imitates/SongLinkも差分更新する（トランザクション）"""
    with transaction.atomic():
        song.title = fields.title
        song.lyrics = fields.lyrics
        song.is_original = fields.is_original
        song.is_deleted = fields.is_deleted
        song.is_joke = fields.is_joke
        song.is_inst = fields.is_inst
        song.is_subeana = fields.is_subeana
        song.is_draft = fields.is_draft
        song.is_questionable = fields.is_questionable
        song.category = fields.category
        song.post_time = timezone.now()
        song.save()
        song.imitates.set(imitate_songs)
        song.authors.set(author_objects)
        existing_links = {link.url: link for link in song.links.all()}
        new_url_set = set(cleaned_url_list)
        for url_str, link in existing_links.items():
            if url_str not in new_url_set:
                link.songs.remove(song)
                # 削除した曲（#1239）に紐づくURLは、曲を復元したときのために残す
                if not Song.all_objects.filter(links=link).exists():
                    link.delete()
        for url_str in new_url_set:
            if url_str not in existing_links:
                link, _ = SongLink.objects.get_or_create(url=url_str)
                link.songs.add(song)


def remove_song(song):
    """Songを論理削除する（#1239）。復元できるよう、URL・作者・模倣元等の関連はそのまま残す"""
    song.is_removed = True
    song.save(update_fields=["is_removed"])


def restore_song(song):
    """論理削除した曲（#1239）の削除を取り消す（#1264）"""
    song.is_removed = False
    song.save(update_fields=["is_removed"])


def get_restore_conflict_songs(song):
    """削除した曲のURLが登録されている、削除していない他の曲を返す。削除を取り消すとURLが重複するため、取り消せない（#1264）"""
    return Song.objects.filter(links__songs=song, links__allow_dup=False).exclude(pk=song.pk).distinct().order_by("id")


def build_delete_discord_text(song, reason, editor):
    """削除用のDiscordテキストを構築する。先頭は新規作成（build_new_song_discord_text）と同じ形式にする"""
    return (
        f"削除されました\n"
        f"{ROOT_URL}/songs/{song.id}\n\n"
        f"タイトル：{song.title}\n"
        f"チャンネル名：{song.authors_str()}\n"
        f"理由：{reason}\n"
        f"編集者：{editor}"
    )


def build_restore_discord_text(song, reason, editor):
    """削除の取り消し用のDiscordテキストを構築する。削除（build_delete_discord_text）と同じ形式にする"""
    return (
        f"削除が取り消されました\n"
        f"{ROOT_URL}/songs/{song.id}\n\n"
        f"タイトル：{song.title}\n"
        f"チャンネル名：{song.authors_str()}\n"
        f"理由：{reason}\n"
        f"編集者：{editor}"
    )


def split_songs_by_category(songs):
    """模倣元・模倣曲の一覧を、そのまま並べる曲・ネタ曲・曲以外のカテゴリごとの曲に分ける（#423）

    曲以外のカテゴリの曲は、ネタ曲かどうかに関わらずカテゴリごとにまとめ、SONG_CATEGORIESの順に並べる。

    Returns:
        dict: songs（そのまま並べる曲）・joke_songs（ネタ曲）・
        category_groups（{"category": SONG_CATEGORIESの要素, "songs": 曲のリスト}のリスト）
    """
    category_songs = {category["value"]: [] for category in SONG_CATEGORIES if category["value"] != "song"}
    main_songs = []
    joke_songs = []
    for song in songs:
        if song.category in category_songs:
            category_songs[song.category].append(song)
        elif song.is_joke:
            joke_songs.append(song)
        else:
            main_songs.append(song)
    category_groups = [
        {"category": category, "songs": category_songs[category["value"]]}
        for category in SONG_CATEGORIES
        if category_songs.get(category["value"])
    ]
    return {"songs": main_songs, "joke_songs": joke_songs, "category_groups": category_groups}


def get_song_links_with_media(song):
    """SongのURLリストをメディア情報付きのdictリストで返す"""
    links = []
    for link in song.links.all():
        media = get_all_media(link.url)
        links.append({
            "text": link.url,
            "icon": media["icon"],
            "name": media["name"],
        })
    return links


def get_song_embeds(links):
    """get_song_links_with_mediaのリンクのうち埋め込めるものを、埋め込み用のURL付きで返す。同じ埋め込みは1つにまとめる（#1254）"""
    embeds = []
    for link in links:
        embed = get_embed(link["text"])
        if embed and all(embed["src"] != added["src"] for added in embeds):
            embeds.append({**embed, "name": link["name"]})
    return embeds


def get_short_base_title(title):
    """short版のタイトルから「short」の部分以降を除いたタイトルを返す。short版でなければNone（#667）

    例：「微細構造[short] (旧:▇)」→「微細構造」、「NNN - short ver.」→「NNN」
    """
    match = SHORT_TOKEN_REGEX.search(title)
    if match is None:
        return None
    return title[:match.start()].strip()


def get_full_base_title(title):
    """タイトルの末尾の「full」の部分を除いたタイトルを返す（#667）

    例：「relix[full]」→「relix」、「チェーン（Full）」→「チェーン」
    """
    return FULL_TOKEN_REGEX.sub("", title).strip()


def get_short_and_full_songs(song):
    """名義が一致し、タイトルからshort版・full版の関係にあると判断できる曲を返す（#667）

    songがshort版ならfull版の候補を、そうでなければshort版の候補を全て返す。
    タイトルは英字の大文字小文字を区別せずに比較する。全角・半角や英字以外の大文字小文字は、
    記号だけのタイトルを取り違えないよう（例：「﹣[short]」と「-」、「Λ [short]」と「λ」）区別する。
    名義は、別名（AuthorAlias）で直接つながっている名義も一致しているとみなす。

    Returns:
        tuple[list[Song], list[Song]]: (full版の曲のリスト, short版の曲のリスト)
    """
    short_base_title = get_short_base_title(song.title)
    base_title = short_base_title if short_base_title is not None else get_full_base_title(song.title)
    if not base_title:
        return [], []

    author_ids = get_same_person_author_ids(song.authors.all())
    candidates = Song.objects.filter(authors__in=author_ids).exclude(id=song.id).distinct().order_by("id").only("id", "title")
    base_title = base_title.translate(ASCII_LOWERCASE_TABLE)

    if short_base_title is not None:
        full_songs = [
            candidate for candidate in candidates
            if get_short_base_title(candidate.title) is None
            and get_full_base_title(candidate.title).translate(ASCII_LOWERCASE_TABLE) == base_title
        ]
        return full_songs, []

    short_songs = [
        candidate for candidate in candidates.filter(title__icontains="short")
        if (get_short_base_title(candidate.title) or "").translate(ASCII_LOWERCASE_TABLE) == base_title
    ]
    return [], short_songs


def build_new_song_discord_text(song_id, fields: SongFields, authors, cleaned_url, editor):
    """新規作成用のchangesリストとDiscordテキストを構築する"""
    COLUMNS = [
        {"label": "タイトル", "value": fields.title},
        {"label": "作者", "value": ", ".join([a.name for a in authors])},
        {"label": "URL", "value": cleaned_url},
        {"label": "カテゴリ", "value": category_label(fields.category)},
        {"label": "オリジナル", "value": yes_no(fields.is_original)},
        {"label": "削除済み", "value": yes_no(fields.is_deleted)},
        {"label": "ネタ曲", "value": yes_no(fields.is_joke)},
        {"label": "インスト曲", "value": yes_no(fields.is_inst)},
        {"label": "すべあな模倣曲", "value": yes_no(fields.is_subeana)},
        {"label": "界隈曲?", "value": yes_no(fields.is_questionable)},
    ]

    changes = [["種類", "内容"]]
    discord_text = f"新規作成されました\n{ROOT_URL}/songs/{song_id}\n\n"
    for column in COLUMNS:
        if column["value"]:
            changes.append([column["label"], column["value"]])
            discord_text += f"**{column['label']}**：`{column['value']}`\n"

    discord_text += f"編集者：`{editor}`"
    return changes, discord_text


def build_edit_song_discord_text(song_id, song, fields: SongFields, author_objects, cleaned_url, imitate_songs):
    """編集用のchangesリスト・Discordテキスト・変更ラベルリストを構築する"""
    def songs_to_info(songs):
        return "\n".join(s.title for s in songs)

    old_imitate_songs = list(song.imitates.all())
    before_urls = ",".join(song.links.order_by('id').values_list('url', flat=True))

    COLUMNS = [
        {"label": "タイトル", "before": song.title, "after": fields.title},
        {"label": "作者", "before": song.authors_str(), "after": ", ".join([a.name for a in author_objects])},
        {"label": "URL", "before": before_urls, "after": cleaned_url},
        {"label": "カテゴリ", "before": category_label(song.category), "after": category_label(fields.category)},
        {"label": "オリジナル", "before": yes_no(song.is_original), "after": yes_no(fields.is_original)},
        {"label": "削除済み", "before": yes_no(song.is_deleted), "after": yes_no(fields.is_deleted)},
        {"label": "ネタ曲", "before": yes_no(song.is_joke), "after": yes_no(fields.is_joke)},
        {"label": "インスト曲", "before": yes_no(song.is_inst), "after": yes_no(fields.is_inst)},
        {"label": "すべあな模倣曲", "before": yes_no(song.is_subeana), "after": yes_no(fields.is_subeana)},
        {"label": "下書き", "before": yes_no(song.is_draft), "after": yes_no(fields.is_draft)},
        {"label": "界隈曲?", "before": yes_no(song.is_questionable), "after": yes_no(fields.is_questionable)},
        {"label": "模倣", "before": songs_to_info(old_imitate_songs), "after": songs_to_info(imitate_songs)},
        {"label": "歌詞", "before": song.lyrics, "after": fields.lyrics.replace("\r\n", "\n")},
    ]

    changes = [["種類", "編集前", "編集後"]]
    changed_labels = []
    discord_text = f"編集されました\n{ROOT_URL}/songs/{song_id}/history\n\n"

    for column in COLUMNS:
        if column["before"] != column["after"]:
            label = column["label"]
            changed_labels.append(label)
            before = column["before"]
            after = column["after"]
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

    edit_title = f"{fields.title}の{'と'.join(changed_labels)}を編集"

    return edit_title, changes, discord_text, changed_labels
