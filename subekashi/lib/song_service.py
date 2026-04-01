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


def build_edit_song_discord_text(song_id, song, title, author_objects, cleaned_url,
                                  before_urls, old_imitate_songs, imitate_songs,
                                  lyrics, is_original, is_deleted, is_joke, is_inst,
                                  is_subeana, is_draft, editor):
    """編集用のchangesリスト・Discordテキスト・変更ラベルリストを構築する"""
    def songs_to_info(songs):
        return "\n".join(s.title for s in songs)

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
