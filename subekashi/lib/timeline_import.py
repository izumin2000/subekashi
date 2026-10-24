from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlparse
from django.db import transaction
from django.utils import timezone
from subekashi.models import Editor, History, Prush, Song, SongLink, SongFields
from subekashi.lib.author_helpers import get_or_create_authors, validate_author_name_lengths
from subekashi.lib.song_service import (
    build_new_song_discord_text,
    category_label,
    check_reject_list,
    create_song,
    get_short_base_title,
)
from subekashi.lib.url import clean_url, get_allow_media
from subekashi.constants.constants import SUBEANA_AUTHOR_ID
import re
import unicodedata


# すべあな界隈年表のカテゴリと、曲のカテゴリ（Song.category）の対応。ここにあるカテゴリの行を登録・更新する
CATEGORY_MAP = {
    "曲": "song",
    "DSC": "song",
    "逆再生枠": "song",
    "アレンジ": "arrange",
    "音mad": "otomad",
    "メドレー": "medley",
    "総集編": "omnibus",
    "予告": "notice",
    "オフボ": "offv",
    "カバー": "cover",
    "ネタ": "meme",
    "": "song",
}

# 登録・更新しないカテゴリ。CATEGORY_MAPにもここにも無いカテゴリは、年表に新しく追加されたものとして知らせる
EXCLUDED_CATEGORIES = {"解読", "その他", "配信", "企画", "出来事", "不明"}

# 年表のモチーフ列で、曲のタイトルと異なる呼び方をしている模倣元
MOTIF_TITLES = {
    "表裏": "表/裏",
    "名の無い星": "名の無い星が空に堕ちたら",
}

# Historyの編集者（開発者）
EDITOR_ID = 1

NICOVIDEO_HOSTS = {"nicovideo.jp", "sp.nicovideo.jp"}

# clean_urlで揃えた後の、動画IDの大文字小文字を区別するURL
CASE_SENSITIVE_URL_PREFIXES = ("youtu.be/", "bilibili.com/video/")

LYRICS_URL_PATTERN = re.compile(r"lyrics\.imicomweb\.com/songs/(\d+)")

VARIATION_SELECTOR = "\ufe0f"
ZERO_WIDTH_JOINER = "\u200d"


# 行を登録・更新しない理由
# 行ごとのトランザクションはロールバックされるが、メモリ上のキャッシュ（曲・URL・模倣・プレラなど）は戻らないため、
# DBやキャッシュを変える前にだけ送出する
class TimelineSkip(Exception):
    pass


@dataclass
class SongState:
    title: str
    category: str
    is_questionable: bool
    prush_id: int | None


@dataclass
class TimelineImportResult:
    created: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    unchanged: int = 0
    excluded: int = 0
    unknown_categories: list = field(default_factory=list)
    skipped: list = field(default_factory=list)


def is_emoji(char):
    # 1F3FB〜1F3FFは肌の色の絵文字修飾子
    return unicodedata.category(char) == "So" or 0x1F3FB <= ord(char) <= 0x1F3FF


# 末尾の絵文字を1文字分削除する。異体字セレクタ付きの絵文字（🌧️）やZWJで繋がった絵文字（👨‍👩‍👧）も1文字として扱う
def remove_last_emoji(text):
    chars = list(text.rstrip(VARIATION_SELECTOR))
    if not chars or not is_emoji(chars[-1]):
        return text
    chars.pop()
    while chars and chars[-1] == ZERO_WIDTH_JOINER:
        chars.pop()
        while chars and chars[-1] == VARIATION_SELECTOR:
            chars.pop()
        if chars and is_emoji(chars[-1]):
            chars.pop()
    return "".join(chars)


# 末尾の作者のバッジ（「🍁+」のような絵文字と「+」）を削除する
def remove_badges(text):
    end = len(text)
    while end and (text[end - 1] in ("+", " ", VARIATION_SELECTOR, ZERO_WIDTH_JOINER) or is_emoji(text[end - 1])):
        end -= 1
    return text[:end]


# モチーフ1は「教育枠」のように末尾に「枠」が付く
def get_motif1_title(text):
    return (text[:-1] if text.endswith("枠") else text).strip()


# モチーフ2は「→.[short]👤」（アレンジ元と作者のバッジ）か「鵺🔢模倣」（模倣元と作者のバッジ）の形式
# 「❁」「全てが適当すぎた.模倣」のように、記号や「模倣」で終わるタイトルの曲もあるため、削る前の文字列から順に模倣元のタイトルの候補を返す
def get_motif2_titles(text):
    if text.startswith("→"):
        # 合作の曲は「→生合成🔢😥」のように作者のバッジが複数付き、「+」が付くこともあるため、バッジを全て削った候補も加える
        text = text[1:]
        candidates = [text, remove_last_emoji(text), remove_badges(text)]
    elif text.endswith("模倣"):
        candidates = [text, text[:-2], remove_badges(text[:-2])]
    else:
        candidates = [text, remove_last_emoji(text)]
    titles = []
    for title in candidates:
        title = title.strip()
        if title and title not in titles:
            titles.append(title)
    return titles


# 合作は作者を改行で区切り、2人目以降の先頭に「+」を付けて書かれていることがある
# 「+SSBA」のように「+」で始まる作者もいるため、1人目の「+」は削らない
def get_author_names(text):
    lines = [line.strip() for line in text.split("\n")]
    names = lines[:1] + [line.lstrip("+").strip() for line in lines[1:]]
    # 空白文字のみの作者名も作者として扱うため、そのまま返す
    return [name for name in names if name] or ([text] if text else [])


# DBには「www.」付き・http・大文字小文字の違うURLもあるため、比較用に揃える
# XのユーザーIDなどは大文字小文字を区別しないため小文字にするが、YouTube・ビリビリ動画の動画IDは区別するためそのままにする
# ニコニコ動画は、スマホ版（sp.nicovideo.jp）や「?ref=」などの付いたURLも同じ動画のURLとして揃える
def get_url_key(url):
    cleaned_url = clean_url(url)
    parsed = urlparse(cleaned_url)
    if parsed.netloc.lower() in NICOVIDEO_HOSTS:
        return f"nicovideo.jp{parsed.path}".rstrip("/").lower()
    key = re.sub(r"^https?://", "", cleaned_url)
    return key if key.startswith(CASE_SENSITIVE_URL_PREFIXES) else key.lower()


# 曲に登録できるURLのみを、短縮・フォーマットして返す
def get_song_urls(urls):
    max_length = SongLink._meta.get_field("url").max_length
    song_urls = []
    for url in urls:
        # 「youtu.be/<id>」のように「https://」の無いURLもある
        if not urlparse(url).scheme:
            url = f"https://{url}"
        for cleaned_url in clean_url(url).split(","):
            cleaned_url = cleaned_url.strip()
            if urlparse(cleaned_url).scheme not in ("http", "https") or not get_allow_media(cleaned_url):
                continue
            if len(cleaned_url) > max_length or cleaned_url in song_urls:
                continue
            song_urls.append(cleaned_url)
    return song_urls


# プレラの名前は、年末のプレラが翌年まで続くときなどに全角・半角が違うことがある（「年末プレラ３」と「年末プレラ3」）ため、揃えて比べる
def get_prush_key(name):
    return unicodedata.normalize("NFKC", name).strip()


# Historyの編集者（開発者）を返す。削除されていたらid=1で作り直す
def get_editor():
    editor, _ = Editor.objects.get_or_create(pk=EDITOR_ID)
    return editor


class TimelineImporter:
    """すべあな界隈年表の行を曲として登録・更新する

    行のURL（URL列・URL2列）が登録されている曲を更新し、どのURLも登録されていなければ曲を新規登録する。
    複数の曲で共有しているURL（allow_dup=True）は、どの曲の行かを決める手がかりにしない。
    どのURLも登録されていなくても、歌詞列がタイトルか作者の一致する曲を指していれば、その曲を更新する。
    ユーザーが削除した曲（#1239）は、削除を取り消さないよう更新も作り直しもしない。
    毎日実行するため、1回の実行で何万回もクエリを発行しないよう、曲・URL・模倣の関係を先に全て読み込んでおく。
    """

    def __init__(self):
        self.result = TimelineImportResult()
        # このrunでカテゴリを決めた曲。複数の行に一致する曲のカテゴリが毎回行ごとに入れ替わらないよう、最初の行のカテゴリにする
        # カテゴリが空欄の行はカテゴリを決めないため含めない
        self.categorized_song_ids = set()
        # このrunでプレラを決めた曲。カテゴリと同様に、最初の行のプレラにする
        self.prushed_song_ids = set()

        self.songs = {
            song_id: SongState(title, category, is_questionable, prush_id)
            for song_id, title, category, is_questionable, prush_id
            in Song.objects.values_list("id", "title", "category", "is_questionable", "prush_id")
        }
        self.title_song_ids = defaultdict(set)
        for song_id, state in self.songs.items():
            self.title_song_ids[state.title].add(song_id)
        self.subeana_song_ids = set(Song.objects.filter(authors=SUBEANA_AUTHOR_ID).values_list("id", flat=True))
        # ユーザーが削除した曲（#1239）。self.songsには含まれないため、照合・更新の対象にしない
        self.removed_song_ids = set(Song.all_objects.filter(is_removed=True).values_list("id", flat=True))

        self.author_names = defaultdict(set)
        for song_id, author_name in Song.authors.through.objects.values_list("song_id", "author__name"):
            self.author_names[song_id].add(author_name)

        self.imitate_ids = defaultdict(set)
        for song_id, imitate_id in Song.imitates.through.objects.values_list("from_song_id", "to_song_id"):
            self.imitate_ids[song_id].add(imitate_id)

        link_song_ids = defaultdict(set)
        for link_id, song_id in SongLink.songs.through.objects.values_list("songlink_id", "song_id"):
            link_song_ids[link_id].add(song_id)
        self.link_ids = {}
        self.url_song_ids = defaultdict(set)
        self.song_url_keys = defaultdict(set)
        # 削除された曲のURL（deleteコマンドでis_removed=Trueになり、どの曲にも紐づいていないか、ユーザーが削除した曲だけに紐づく）
        self.removed_url_keys = set()
        # 複数の曲で共有しているURL（メドレーの動画やチャンネルのURLなど）
        self.shared_url_keys = set()
        for link_id, url, is_removed, allow_dup in SongLink.objects.values_list("id", "url", "is_removed", "allow_dup"):
            key = get_url_key(url)
            song_ids = link_song_ids[link_id] - self.removed_song_ids
            self.link_ids.setdefault(key, link_id)
            self.url_song_ids[key] |= song_ids
            for song_id in song_ids:
                self.song_url_keys[song_id].add(key)
            if (is_removed or link_song_ids[link_id]) and not song_ids:
                self.removed_url_keys.add(key)
            if allow_dup:
                self.shared_url_keys.add(key)

        self.prush_names = {}
        self.prush_dates = {}
        # 全角・半角だけが違うプレラが複数登録されている場合は、先に登録されたプレラを使う
        self.prush_ids = {}
        for prush_id, name, prush_date in Prush.objects.order_by("id").values_list("id", "name", "date"):
            self.prush_names[prush_id] = name
            self.prush_dates[prush_id] = prush_date
            self.prush_ids.setdefault(get_prush_key(name), prush_id)

    # プレラのidを返す。無ければその行の日付で作る
    # 行をスキップすると作ったプレラはロールバックされるため、スキップすることが無くなってから呼ぶ
    def get_prush_id(self, row):
        key = get_prush_key(row.premiere_rush)
        if key not in self.prush_ids:
            prush = Prush.objects.create(name=row.premiere_rush, date=row.date)
            self.prush_ids[key] = prush.id
            self.prush_names[prush.id] = prush.name
            self.prush_dates[prush.id] = prush.date
        return self.prush_ids[key]

    # プレラの日付は、年表でそのプレラが最初に出てくる行の日付にする
    # 曲の検索の選択肢の並びに使うため、曲を登録・更新しない行（対象外のカテゴリ・スキップした行）の日付も使う
    def update_prush_date(self, row):
        prush_id = self.prush_ids.get(get_prush_key(row.premiere_rush)) if row.premiere_rush else None
        if prush_id is None or row.date is None:
            return
        if self.prush_dates.get(prush_id) is None or row.date < self.prush_dates[prush_id]:
            Prush.objects.filter(pk=prush_id).update(date=row.date)
            self.prush_dates[prush_id] = row.date

    def is_removed_url(self, key):
        return key in self.removed_url_keys and not self.url_song_ids[key]

    # タイトルの候補のうち、曲がある最初の候補の曲を返す
    # 模倣元は多くがすべあなの曲で、同じタイトルのアレンジなども登録されているため、同じタイトルの曲が複数あればすべあなの曲に決める
    # すべあなの曲に決まらなければ、どの曲か決められないため模倣に追加しない
    # 曲のタイトルは最初に全て読み込んでいるため、行ごとにクエリは発行しない
    def find_imitate_id(self, titles):
        for title in titles:
            song_ids = self.title_song_ids.get(MOTIF_TITLES.get(title, title))
            if not song_ids:
                continue
            song_ids = (song_ids & self.subeana_song_ids) or song_ids
            return next(iter(song_ids)) if len(song_ids) == 1 else None
        return None

    def get_imitate_ids(self, row):
        motif1_titles = [title for title in [get_motif1_title(row.motif1)] if title]
        imitate_ids = [
            self.find_imitate_id(motif1_titles),
            self.find_imitate_id(get_motif2_titles(row.motif2)),
        ]
        return {imitate_id for imitate_id in imitate_ids if imitate_id}

    # 歌詞列（https://lyrics.imicomweb.com/songs/<id>）が指す曲のidを返す
    # 歌詞列が別の曲を指していることもあるため、タイトルか作者が一致しなければスキップする
    def get_lyrics_song_id(self, row):
        match = LYRICS_URL_PATTERN.search(row.lyrics_url)
        if not match:
            return None
        song_id = int(match[1])
        # ユーザーが削除した曲を作り直さないよう、新規作成もしない
        if song_id in self.removed_song_ids:
            raise TimelineSkip("歌詞列の曲が削除されている")
        state = self.songs.get(song_id)
        if state is None:
            return None
        if row.title == state.title:
            return song_id
        if not self.author_names[song_id] & set(get_author_names(row.author)):
            raise TimelineSkip("歌詞列の曲とタイトル・作者が一致しない")
        # full版の行の歌詞列がshort版の曲を指していることもあるため、作者だけが一致する場合はshort版かどうかも同じ曲に限る
        if (get_short_base_title(row.title) is None) != (get_short_base_title(state.title) is None):
            raise TimelineSkip("歌詞列の曲とshort版かどうかが異なる")
        return song_id

    def add_url(self, song, url):
        key = get_url_key(url)
        link_id = self.link_ids.get(key) or SongLink.objects.create(url=url).id
        song.links.add(link_id)
        self.link_ids[key] = link_id
        self.url_song_ids[key].add(song.id)
        self.song_url_keys[song.id].add(key)

    def create(self, row, urls, category, imitate_ids):
        if any(self.is_removed_url(get_url_key(url)) for url in urls):
            raise TimelineSkip("削除された曲のURL")
        if not row.title:
            raise TimelineSkip("タイトルが空")
        if len(row.title) > Song._meta.get_field("title").max_length:
            raise TimelineSkip("タイトルが長すぎる")
        author_names = get_author_names(row.author)
        if not author_names:
            raise TimelineSkip("作者が空")
        if validate_author_name_lengths(author_names):
            raise TimelineSkip("作者名が長すぎる")
        authors = get_or_create_authors(author_names)
        if check_reject_list(authors):
            raise TimelineSkip("掲載拒否の作者")

        fields = SongFields(title=row.title, category=category)
        song = create_song(fields)
        song.authors.set(authors)
        for url in urls:
            self.add_url(song, url)
        song.imitates.add(*imitate_ids)
        if row.premiere_rush:
            song.prush_id = self.get_prush_id(row)
            song.save(update_fields=["prush"])

        editor = get_editor()
        changes, _ = build_new_song_discord_text(song.id, fields, authors, ",".join(urls), editor)
        if song.prush_id:
            changes.append(["プレラ", self.prush_names[song.prush_id]])
        if imitate_ids:
            changes.append(["模倣", "\n".join(Song.objects.filter(id__in=imitate_ids).order_by("id").values_list("title", flat=True))])
        History.create_for_song(
            song=song,
            title=f"{song.title}を新規作成",
            history_type="new",
            changes=changes,
            editor=editor,
        )

        self.songs[song.id] = SongState(song.title, song.category, song.is_questionable, song.prush_id)
        self.title_song_ids[song.title].add(song.id)
        self.imitate_ids[song.id] |= imitate_ids
        self.author_names[song.id] = {author.name for author in authors}
        if any(author.id == SUBEANA_AUTHOR_ID for author in authors):
            self.subeana_song_ids.add(song.id)
        if row.category:
            self.categorized_song_ids.add(song.id)
        if row.premiere_rush:
            self.prushed_song_ids.add(song.id)
        self.result.created.append(song)

    def update(self, song_id, row, urls, category, imitate_ids):
        state = self.songs[song_id]

        new_urls = [
            url for url in urls
            if get_url_key(url) not in self.song_url_keys[song_id] and not self.is_removed_url(get_url_key(url))
        ]
        # 界隈曲?の曲は、編集画面と同様に模倣を登録しない
        new_imitate_ids = set() if state.is_questionable else imitate_ids - self.imitate_ids[song_id] - {song_id}
        # カテゴリが空欄の行（categoryがNone）は、サイトで設定されたカテゴリを変えない
        new_category = None
        if category:
            if song_id not in self.categorized_song_ids and category != state.category:
                new_category = category
            self.categorized_song_ids.add(song_id)
        # プ列が空欄の行は、登録されているプレラを消さない
        prush_name = row.premiere_rush
        new_prush_id = None
        if prush_name:
            current_key = get_prush_key(self.prush_names[state.prush_id]) if state.prush_id else None
            if song_id not in self.prushed_song_ids and get_prush_key(prush_name) != current_key:
                new_prush_id = self.get_prush_id(row)
            self.prushed_song_ids.add(song_id)
        if not (new_urls or new_imitate_ids or new_category or new_prush_id):
            self.result.unchanged += 1
            return

        song = Song.objects.get(pk=song_id)
        changes = [["種類", "編集前", "編集後"]]
        labels = []

        if new_urls:
            before = ",".join(song.links.order_by("id").values_list("url", flat=True))
            for url in new_urls:
                self.add_url(song, url)
            after = ",".join(song.links.order_by("id").values_list("url", flat=True))
            changes.append(["URL", before, after])
            labels.append("URL")

        if new_category:
            changes.append(["カテゴリ", category_label(song.category), category_label(new_category)])
            labels.append("カテゴリ")
            song.category = new_category
            state.category = new_category

        if new_prush_id:
            changes.append(["プレラ", self.prush_names.get(song.prush_id, ""), self.prush_names[new_prush_id]])
            labels.append("プレラ")
            song.prush_id = new_prush_id
            state.prush_id = new_prush_id

        if new_imitate_ids:
            before = "\n".join(song.imitates.order_by("id").values_list("title", flat=True))
            song.imitates.add(*new_imitate_ids)
            after = "\n".join(song.imitates.order_by("id").values_list("title", flat=True))
            changes.append(["模倣", before, after])
            labels.append("模倣")
            self.imitate_ids[song_id] |= new_imitate_ids

        # 実行中に編集画面で行われた変更を上書きしないよう、変更するフィールドのみを保存する
        Song.objects.filter(pk=song_id).update(category=song.category, prush=song.prush_id, post_time=timezone.now())
        history = History.create_for_song(
            song=song,
            title=f"{song.title}の{'と'.join(labels)}を編集",
            history_type="edit",
            changes=changes,
            editor=get_editor(),
        )
        self.result.updated.append((song, history))

    def import_row(self, row):
        self.update_prush_date(row)
        category = CATEGORY_MAP.get(row.category)
        if category is None:
            if row.category in EXCLUDED_CATEGORIES:
                self.result.excluded += 1
            else:
                self.result.unknown_categories.append(row)
            return

        try:
            urls = get_song_urls(row.urls)
            if not urls:
                raise TimelineSkip("登録できるURLが無い")

            # 複数の曲で共有しているURL（allow_dup=True）は、どの曲の行かを決める手がかりにしない
            keys = [get_url_key(url) for url in urls if get_url_key(url) not in self.shared_url_keys]
            song_ids = set().union(*(self.url_song_ids[key] for key in keys))
            if len(song_ids) > 1:
                raise TimelineSkip("複数の曲に一致")

            imitate_ids = self.get_imitate_ids(row)
            with transaction.atomic():
                song_id = song_ids.pop() if song_ids else self.get_lyrics_song_id(row)
                if song_id:
                    self.update(song_id, row, urls, category if row.category else None, imitate_ids)
                elif not keys:
                    # 共有しているURLしか無い行は、次の実行でもURLで照合できず毎日新規作成されてしまうため登録しない
                    raise TimelineSkip("複数の曲で共有しているURLのみ")
                else:
                    self.create(row, urls, category, imitate_ids)

        except TimelineSkip as e:
            self.result.skipped.append((row, str(e)))


def import_timeline(rows):
    importer = TimelineImporter()
    for row in rows:
        importer.import_row(row)
    return importer.result
