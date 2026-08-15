from config.settings import ROOT_URL


def build_new_alias_discord_text(author, alias, editor):
    """別名新規追加用のDiscordテキストを構築する"""
    return (
        f"別名が追加されました\n"
        f"{ROOT_URL}/authors/{author.id}/aliases\n\n"
        f"**作者**：`{author.name}`\n"
        f"**別名**：`{alias.name}`\n"
        f"**種別**：`{alias.get_alias_type_display()}`\n"
        f"編集者：`{editor}`"
    )


def build_edit_alias_discord_text(author, old_name, changes, editor):
    """別名編集用のDiscordテキストを構築する

    changesは [["種類", "編集前", "編集後"], [label, before, after], ...] の形式
    （実際に変更されたラベルのみを含む）
    """
    discord_text = (
        f"別名が編集されました\n"
        f"{ROOT_URL}/authors/{author.id}/aliases\n\n"
        f"**作者**：`{author.name}`\n"
    )
    for label, before, after in changes[1:]:
        discord_text += f"**{label}**：`{before}` :arrow_right: `{after}`\n"
    discord_text += f"編集者：`{editor}`"
    return discord_text


def build_delete_alias_discord_text(author, alias_name, editor):
    """別名削除用のDiscordテキストを構築する"""
    return (
        f"別名が削除されました\n"
        f"{ROOT_URL}/authors/{author.id}/aliases\n\n"
        f"**作者**：`{author.name}`\n"
        f"**別名**：`{alias_name}`\n"
        f"編集者：`{editor}`"
    )


def build_set_primary_name_discord_text(author, old_name, new_name, editor):
    """一番有名な名義の変更用のDiscordテキストを構築する（#1008）"""
    return (
        f"一番有名な名義が変更されました\n"
        f"{ROOT_URL}/authors/{author.id}/aliases\n\n"
        f"**変更前**：`{old_name}`\n"
        f"**変更後**：`{new_name}`\n"
        f"編集者：`{editor}`"
    )
