from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from config.local_settings import NEW_DISCORD_URL
from subekashi.models import Author, AuthorAlias, Editor, History
from subekashi.forms import AuthorAliasForm, AuthorPrimaryNameForm
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.author_alias_service import (
    build_new_alias_discord_text,
    build_edit_alias_discord_text,
    build_delete_alias_discord_text,
    build_set_primary_name_discord_text,
)


LINKABLE_ALIAS_TYPES = ("past", "another", "group")
DUPLICATE_NAME_ERROR = "その別名は既に登録されています。"

CHANNEL_LINK_NOTE = "対応する名義が存在する場合、一覧画面でチャンネルページへのリンクが表示されます。"

ALIAS_TYPE_DESCRIPTIONS = {
    "id": "YouTubeチャンネルIDなど、名前ではなく識別子としての別名です。",
    "abbr": "作者名を短縮した略称です。",
    "common": "正式名称ではないが、広く使われている呼び方です。",
    "past": f"以前使用されていた名称です。{CHANNEL_LINK_NOTE}",
    "sns": "SNS上で使われている名称です。",
    "spell": "表記揺れ（ひらがな・カタカナ・英字表記の違いなど）です。",
    "another": f"同一人物が運用している、本人公認の別名義です。曲検索では自動的に同一視されません。{CHANNEL_LINK_NOTE}",
    "group": f"合作アカウント等、複数人で運用している名義です。{CHANNEL_LINK_NOTE}",
}


def alias_type_choices():
    """new/edit画面のalias_typeフォーム用の選択肢（各選択肢の説明文付き）を返す"""
    return [
        {"value": value, "label": label, "description": ALIAS_TYPE_DESCRIPTIONS.get(value, "")}
        for value, label in AuthorAlias.CHOICES
    ]


class AuthorAliasesView(View):
    def get(self, request, author_id):
        author = Author.get_or_none(author_id)
        if author is None:
            return render(request, 'subekashi/404.html', status=404)

        transitive_aliases = author.get_transitive_aliases()

        # get_transitive_aliases()が追加クエリなしに解決できなかった行（正方向かつ
        # another/groupのリーフエッジのみ）に限定して、対応する実在Authorのidを
        # 補完的に一括取得する。対象はクラスタ全体ではなく未解決の一部の名前に限られる
        # ため、クラスタが大きくなってもこのクエリのIN句が際限なく大きくなることはない（#1023）
        unresolved_names = [ta.name for ta in transitive_aliases if ta.author_id is None]
        resolved_ids_by_name = dict(
            Author.objects.filter(name__in=unresolved_names).values_list("name", "id")
        ) if unresolved_names else {}

        alias_rows = []
        for ta in transitive_aliases:
            is_editable = ta.is_direct and not ta.is_reverse
            matched_author_id = ta.author_id if ta.author_id is not None else resolved_ids_by_name.get(ta.name)

            # 別名自体(ta.name)に対応する実在Authorを優先して遷移先にする。
            # 対応するAuthorがない場合、このAuthorAlias自体を実際に所有している
            # author(source.author)へフォールバックする（所有者は必ず実在するため
            # 確実にリンクできる）。編集可能な行（is_editable=True）はsource.authorが
            # 常に自分自身であるため、下のif next_alias_author_id == author.idで
            # 結果的にNoneに戻る（フォールバックしても意味がないという意図の通り）
            next_alias_author_id = matched_author_id
            if next_alias_author_id is None:
                next_alias_author_id = ta.source.author_id

            if next_alias_author_id == author.id:
                # 遷移先が現在表示中のページ自身の場合はリンクを出さない
                next_alias_author_id = None

            alias_rows.append({
                "name": ta.name,
                "alias_type_display": ta.alias_type_display,
                "is_editable": is_editable,
                "alias_id": ta.source.id,
                "show_channel_link": ta.alias_type in LINKABLE_ALIAS_TYPES and matched_author_id is not None,
                "next_alias_author_id": next_alias_author_id,
            })

        context = {
            "metatitle": f"{author.name}の別名一覧",
            "author": author,
            "alias_rows": alias_rows,
            # 一番有名な名義の選択肢（#1008）。候補は現在の名前 + alias_type="past"の別名のみ
            "primary_name_candidates": [author.name] + list(
                author.aliases.filter(alias_type="past").values_list("name", flat=True)
            ),
        }
        return render(request, 'subekashi/author_aliases.html', context)


class AuthorAliasNewView(View):
    def dispatch(self, request, author_id, *args, **kwargs):
        self.author = Author.get_or_none(author_id)
        if self.author is None:
            return render(request, 'subekashi/404.html', status=404)
        return super().dispatch(request, author_id, *args, **kwargs)

    def get_base_context(self):
        return {
            "metatitle": f"{self.author.name}の別名を追加",
            "author": self.author,
            "alias_type_choices": alias_type_choices(),
        }

    def get(self, request, author_id):
        return render(request, 'subekashi/author_alias_new.html', self.get_base_context())

    def post(self, request, author_id):
        context = self.get_base_context()
        form = AuthorAliasForm(request.POST, author=self.author)

        if not form.is_valid():
            context["error"] = list(form.errors.values())[0][0]
            return render(request, 'subekashi/author_alias_new.html', context)

        # 未保存のAuthorAliasインスタンスでDiscordテキストを構築し、
        # 通知が成功した場合のみDBへコミットする（Deleteと同じ「通知成功後にDB確定」パターン）
        alias = AuthorAlias(
            name=form.cleaned_data['name'],
            alias_type=form.cleaned_data['alias_type'],
            author=self.author,
        )
        editor = Editor.get_or_create_from_ip(get_ip(request))

        discord_text = build_new_alias_discord_text(self.author, alias, editor)
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)

        try:
            with transaction.atomic():
                alias.save()
                History.create_for_author(
                    author=self.author,
                    title=f"別名『{alias.name}』を追加",
                    history_type="new",
                    changes=[["種類", "内容"], ["別名", alias.name], ["種別", alias.get_alias_type_display()]],
                    editor=editor,
                )
        except IntegrityError:
            # ほぼ同時に同名の別名がPOSTされた場合のTOCTOU対策
            # （フォームのclean_name()での重複チェックをすり抜けてDB制約に抵触するケース）
            context["error"] = DUPLICATE_NAME_ERROR
            return render(request, 'subekashi/author_alias_new.html', context)

        return redirect(f"{reverse('subekashi:author_aliases', args=[self.author.id])}?toast=new")


class AuthorAliasEditView(View):
    def dispatch(self, request, author_id, alias_id, *args, **kwargs):
        self.author = Author.get_or_none(author_id)
        if self.author is None:
            return render(request, 'subekashi/404.html', status=404)
        self.alias = AuthorAlias.objects.filter(pk=alias_id, author=self.author).first()
        if self.alias is None:
            return render(request, 'subekashi/404.html', status=404)
        return super().dispatch(request, author_id, alias_id, *args, **kwargs)

    def get_base_context(self):
        return {
            "metatitle": f"{self.author.name}の別名『{self.alias.name}』を編集",
            "author": self.author,
            "alias": self.alias,
            "alias_type_choices": alias_type_choices(),
        }

    def get(self, request, author_id, alias_id):
        return render(request, 'subekashi/author_alias_edit.html', self.get_base_context())

    def post(self, request, author_id, alias_id):
        context = self.get_base_context()
        form = AuthorAliasForm(request.POST, author=self.author, editing_alias=self.alias)

        if not form.is_valid():
            context["error"] = list(form.errors.values())[0][0]
            return render(request, 'subekashi/author_alias_edit.html', context)

        old_name = self.alias.name
        old_alias_type_display = self.alias.get_alias_type_display()

        # 変更内容の判定はDBへの保存前に行う（未保存のインスタンスに対してフィールドを
        # 書き換えるだけなので、このリクエスト内で破棄されても副作用はない）
        self.alias.name = form.cleaned_data['name']
        self.alias.alias_type = form.cleaned_data['alias_type']
        new_alias_type_display = self.alias.get_alias_type_display()

        changes = [["種類", "編集前", "編集後"]]
        if old_name != self.alias.name:
            changes.append(["別名", old_name, self.alias.name])
        if old_alias_type_display != new_alias_type_display:
            changes.append(["種別", old_alias_type_display, new_alias_type_display])

        # 実質的な変更がない場合は保存・履歴作成・Discord通知をスキップする（SongEditViewと同様の挙動）
        if len(changes) <= 1:
            return redirect(f"{reverse('subekashi:author_aliases', args=[self.author.id])}?toast=edit")

        # Discordへの通知が成功した場合のみDBへコミットする
        # （Deleteと同じ「通知成功後にDB確定」パターン。通知に失敗した場合、
        # self.aliasへの変更は未保存のままリクエストの終了とともに破棄される）
        editor = Editor.get_or_create_from_ip(get_ip(request))
        discord_text = build_edit_alias_discord_text(self.author, old_name, changes, editor)
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)

        try:
            with transaction.atomic():
                self.alias.save()
                History.create_for_author(
                    author=self.author,
                    title=f"別名『{old_name}』を編集",
                    history_type="edit",
                    changes=changes,
                    editor=editor,
                )
        except IntegrityError:
            # ほぼ同時に同名の別名がPOSTされた場合のTOCTOU対策
            self.alias.refresh_from_db()
            context["error"] = DUPLICATE_NAME_ERROR
            return render(request, 'subekashi/author_alias_edit.html', context)

        return redirect(f"{reverse('subekashi:author_aliases', args=[self.author.id])}?toast=edit")


class AuthorAliasDeleteView(View):
    def dispatch(self, request, author_id, alias_id, *args, **kwargs):
        self.author = Author.get_or_none(author_id)
        if self.author is None:
            return render(request, 'subekashi/404.html', status=404)
        self.alias = AuthorAlias.objects.filter(pk=alias_id, author=self.author).first()
        if self.alias is None:
            return render(request, 'subekashi/404.html', status=404)
        return super().dispatch(request, author_id, alias_id, *args, **kwargs)

    def get(self, request, author_id, alias_id):
        context = {
            "metatitle": f"{self.author.name}の別名『{self.alias.name}』を削除",
            "author": self.author,
            "alias": self.alias,
        }
        return render(request, 'subekashi/author_alias_delete.html', context)

    def post(self, request, author_id, alias_id):
        editor = Editor.get_or_create_from_ip(get_ip(request))
        alias_name = self.alias.name

        # Discordへの通知が成功した場合のみ実際に削除する
        # （通知できないまま消えると荒らし行為等の運用上の可視性が失われるため）
        discord_text = build_delete_alias_discord_text(self.author, alias_name, editor)
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)

        with transaction.atomic():
            History.create_for_author(
                author=self.author,
                title=f"別名『{alias_name}』を削除",
                history_type="delete",
                changes=None,
                editor=editor,
            )
            self.alias.delete()

        return redirect(f"{reverse('subekashi:author_aliases', args=[self.author.id])}?toast=delete")


class AuthorPrimaryNameSetView(View):
    """一番有名な名義の変更（#1008）

    author.nameと、選択されたalias_type="past"のAuthorAlias.nameを入れ替える。
    Song.authorsはAuthorのPK参照のため、この入れ替えだけで既存のSongデータは
    一切変更せずに表示上の正規化が完了する。選択した名前が既存の別のAuthorの
    名前と衝突する場合はAuthorPrimaryNameForm側で選択不可としており、
    マージ（Song・AuthorAliasの付け替え）は行わない。
    """
    def dispatch(self, request, author_id, *args, **kwargs):
        self.author = Author.get_or_none(author_id)
        if self.author is None:
            return render(request, 'subekashi/404.html', status=404)
        return super().dispatch(request, author_id, *args, **kwargs)

    def post(self, request, author_id):
        base_url = reverse('subekashi:author_aliases', args=[self.author.id])
        form = AuthorPrimaryNameForm(request.POST, author=self.author)

        if not form.is_valid():
            return redirect(f"{base_url}?toast=primary_error")

        new_name = form.cleaned_data['name']
        old_name = self.author.name

        if new_name == old_name:
            return redirect(base_url)

        editor = Editor.get_or_create_from_ip(get_ip(request))

        # Discordへの通知が成功した場合のみDBへコミットする
        # （New/Edit/Deleteと同じ「通知成功後にDB確定」パターン）
        discord_text = build_set_primary_name_discord_text(self.author, old_name, new_name, editor)
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)

        try:
            with transaction.atomic():
                # 選択された側のAuthorAlias行は、これからauthor自身の名前になるため削除する
                AuthorAlias.objects.get(author=self.author, name=new_name, alias_type="past").delete()
                self.author.name = new_name
                self.author.save()
                # 旧名を新たな「以前の名称」として登録し直す
                AuthorAlias.objects.create(name=old_name, author=self.author, alias_type="past")
                History.create_for_author(
                    author=self.author,
                    title=f"一番有名な名義を『{new_name}』に変更",
                    history_type="edit",
                    changes=[["種類", "編集前", "編集後"], ["一番有名な名義", old_name, new_name]],
                    editor=editor,
                )
        except IntegrityError:
            # ほぼ同時に同名の別名が別途登録された場合等のTOCTOU対策
            return redirect(f"{base_url}?toast=primary_error")

        return redirect(f"{base_url}?toast=primary")
