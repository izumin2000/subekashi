from dataclasses import dataclass
from config.settings import ROOT_URL
from subekashi.models import Author, Song


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


@dataclass
class UnifyNamePlan:
    """名義の統一（#1137）で行う変更内容

    target_authorは統一先のAuthor。選択した名義と同名の既存Authorがあればそれ、
    なければauthor自身（選択した名義が以前の名称なら、authorをその名前に変更する）。
    source_authorsは候補の名義（authorの名前＋以前の名称）と同名のAuthorのうち、
    統一先以外のもの。これらの曲は統一先へ移すが、Author自体は削除しない。
    """
    author: Author
    old_name: str
    new_name: str
    target_author: Author
    source_authors: list

    @property
    def renames_author(self):
        return self.target_author.pk == self.author.pk and self.new_name != self.old_name

    @property
    def moves_to_existing_author(self):
        return self.target_author.pk != self.author.pk

    def song_author_pairs(self):
        """統一先へ移す曲の(song_id, author_id)の一覧を返す"""
        return list(
            Song.authors.through.objects.filter(author__in=self.source_authors).values_list("song_id", "author_id")
        )

    def affected_source_authors(self, song_author_pairs):
        """source_authorsのうち、統一により実際に変更が及ぶものを返す

        曲を持たないAuthorは何も変わらないため除く。ただし統一先が既存の別Authorの
        場合のauthor自身は、曲の有無に関わらず別名・リンクを統一先へ移すため含める
        """
        moved_author_ids = {author_id for _, author_id in song_author_pairs}
        return [a for a in self.source_authors if a.pk in moved_author_ids or a.pk == self.author.pk]


def build_unify_name_plan(author, new_name):
    past_names = list(author.aliases.filter(alias_type="past").values_list("name", flat=True))
    other_authors = list(Author.objects.filter(name__in=past_names).exclude(pk=author.pk))
    target_author = next((a for a in other_authors if a.name == new_name), author)
    source_authors = [a for a in [author] + other_authors if a.pk != target_author.pk]
    return UnifyNamePlan(
        author=author,
        old_name=author.name,
        new_name=new_name,
        target_author=target_author,
        source_authors=source_authors,
    )


def build_unify_name_discord_text(target_author, old_name, new_name, editor, source_authors=()):
    """名義の統一用のDiscordテキストを構築する（#1137）

    source_authorsには、曲（統一先が既存の別Authorの場合は別名・リンクも）を
    統一先へ移したAuthorを渡す
    """
    rename_note = f"**変更前**：`{old_name}`\n" if old_name != new_name else ""
    source_note = (
        "**統一元**：" + ", ".join(f"`Author(id={a.id}, name={a.name})`" for a in source_authors) + "\n"
        if source_authors else ""
    )
    return (
        f"名義が統一されました\n"
        f"{ROOT_URL}/authors/{target_author.id}/aliases\n\n"
        f"{rename_note}"
        f"**統一後**：`{new_name}`\n"
        f"{source_note}"
        f"編集者：`{editor}`"
    )
