from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from config.local_settings import NEW_DISCORD_URL
from subekashi.models import Author, AuthorAlias, AuthorLink, Editor, History, Song
from subekashi.forms import AuthorAliasForm, AuthorUnifyNameForm
from subekashi.lib.ip import get_ip
from subekashi.lib.discord import send_discord
from subekashi.lib.author_alias_service import (
    build_new_alias_discord_text,
    build_edit_alias_discord_text,
    build_delete_alias_discord_text,
    build_unify_name_discord_text,
    build_unify_name_plan,
)


LINKABLE_ALIAS_TYPES = ("past", "another", "group")
DUPLICATE_NAME_ERROR = "その別名は既に登録されています。"

CHANNEL_LINK_NOTE = "対応する名義が存在する場合、一覧画面でチャンネルページへのリンクが表示されます。"

ALIAS_TYPE_DESCRIPTIONS = {
    "id": "YouTubeチャンネルIDなど、名前ではなく識別子としての別名です。",
    "abbr": "作者名を短縮した略称です。",
    "common": "正式名称ではないが、広く使われている呼び方です。",
    "past": f"以前使用されていた名称です。別名一覧画面の「名義を統一する」で統一先として選択でき、選択するとこの名前が今後の作者の表示名になります。{CHANNEL_LINK_NOTE}",
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
            # 名義の統一先の選択肢（#1008、#1137）。候補は現在の名前 + alias_type="past"の別名のみで、
            # ここでは現在の名前以外を渡す
            "unify_name_sources": list(
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


# SongEditViewと同様、キャッシュされた古いフォームの送信で編集が巻き戻らないようにする（#1135）
@method_decorator(never_cache, name='dispatch')
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


class AuthorUnifyNameConfirmView(View):
    """名義の統一前の確認画面（#1029、#1137）

    統一により、候補の名義と同名の別Authorの曲が統一先へ移る。これはIPアドレスのみで
    判別する匿名の編集者でも実行できてしまうため、実際に統一する前に内容を確認できる
    ワンクッションを挟む。
    """
    def dispatch(self, request, author_id, *args, **kwargs):
        self.author = Author.get_or_none(author_id)
        if self.author is None:
            return render(request, 'subekashi/404.html', status=404)
        return super().dispatch(request, author_id, *args, **kwargs)

    def get(self, request, author_id):
        base_url = reverse('subekashi:author_aliases', args=[self.author.id])
        form = AuthorUnifyNameForm(request.GET, author=self.author)

        if not form.is_valid():
            return redirect(f"{base_url}?toast=unify_error")

        plan = build_unify_name_plan(self.author, form.cleaned_data['name'])
        song_author_pairs = plan.song_author_pairs()
        if not plan.renames_author and not plan.moves_to_existing_author and not song_author_pairs:
            return redirect(f"{base_url}?toast=unify_noop")

        # 統一によって表示上の作者名が変わる曲を一覧できるようにする。曲を移すAuthorの曲に加え、
        # authorの名前を変更する場合は元々authorに紐づく曲も対象になる。同じ曲が複数の
        # Authorの共著になっているケースに備え、Song単位でdistinct()する
        song_filter = Q(pk__in={song_id for song_id, _ in song_author_pairs})
        if plan.renames_author:
            song_filter |= Q(authors=self.author)
        song_titles = list(Song.objects.filter(song_filter).distinct().values_list("title", flat=True))

        context = {
            "metatitle": f"{self.author.name}の名義の統一を確認",
            "author": self.author,
            "new_name": plan.new_name,
            "target_author": plan.target_author if plan.moves_to_existing_author else None,
            "source_authors": [
                a for a in plan.affected_source_authors(song_author_pairs) if a.pk != self.author.pk
            ],
            "song_titles": song_titles,
        }
        return render(request, 'subekashi/author_unify_name_confirm.html', context)


class AuthorUnifyNameSetView(View):
    """名義の統一（#1008、#1029、#1137）

    候補の名義（author.name + alias_type="past"の別名）と同名のAuthorに紐づく曲を、
    選択した名義のAuthor（統一先）へ全て移す。曲を移したAuthor自体は削除せず、曲数が0になるだけ。

    統一先は、選択した名義と同名の既存Authorがあればそれ、なければauthor自身。
    - author自身が統一先で、以前の名称を選択した場合: author.nameと選択したAuthorAlias.nameを
      入れ替える。Song.authorsはAuthorのPK参照のため、元々authorに紐づく曲はSongデータを
      変更せずに表示上の作者名が変わる
    - 既存の別Authorが統一先の場合: Author.nameはuniqueでauthorをその名前に変更できないため、
      authorの曲に加えて別名・リンクも統一先へ移し、authorの旧名を統一先の以前の名称として登録する
    """
    def dispatch(self, request, author_id, *args, **kwargs):
        self.author = Author.get_or_none(author_id)
        if self.author is None:
            return render(request, 'subekashi/404.html', status=404)
        return super().dispatch(request, author_id, *args, **kwargs)

    def post(self, request, author_id):
        base_url = reverse('subekashi:author_aliases', args=[self.author.id])
        form = AuthorUnifyNameForm(request.POST, author=self.author)

        if not form.is_valid():
            return redirect(f"{base_url}?toast=unify_error")

        new_name = form.cleaned_data['name']
        old_name = self.author.name
        plan = build_unify_name_plan(self.author, new_name)
        song_author_pairs = plan.song_author_pairs()

        if not plan.renames_author and not plan.moves_to_existing_author and not song_author_pairs:
            return redirect(f"{base_url}?toast=unify_noop")

        # 旧名(old_name)は統一先の新たなpast別名として登録し直すが、AuthorAlias.nameは
        # グローバルにunique（他のauthorが既にold_nameと同名の別名を持つ「逆方向」の
        # 関係は正常な状態としてありうる）なため、衝突している場合は登録できない。
        # ただしauthor・統一先自身が持つ別名は、統一後は統一先のものとして再利用するため対象外とする。
        # これは同時実行のレースではなく既存データ次第で毎回決定的に失敗するため、
        # Discord通知を送る前に弾く（通知だけ成功してDBが更新されない不整合を避ける）
        if old_name != new_name and AuthorAlias.objects.filter(name=old_name).exclude(
            author__in=[self.author, plan.target_author]
        ).exists():
            return redirect(f"{base_url}?toast=unify_error")

        editor = Editor.get_or_create_from_ip(get_ip(request))

        # Discordへの通知が成功した場合のみDBへコミットする
        # （New/Edit/Deleteと同じ「通知成功後にDB確定」パターン）
        discord_text = build_unify_name_discord_text(
            plan.target_author, old_name, new_name, editor,
            source_authors=plan.affected_source_authors(song_author_pairs),
        )
        is_ok = send_discord(NEW_DISCORD_URL, discord_text)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)

        # send_discord()（ネットワークI/O）の完了を待つ間に、別のリクエストが対象の
        # past別名を変更・削除してしまうTOCTOU対策。.get()だとDoesNotExistが
        # IntegrityError以外の未処理の例外として伝播してしまうため、.filter().first()で
        # Noneチェックしてから同じtoast=unify_errorに倒す（他の分岐と挙動を揃える）
        selected_alias = None
        if new_name != old_name:
            selected_alias = AuthorAlias.objects.filter(
                author=self.author, name=new_name, alias_type="past"
            ).first()
            if selected_alias is None:
                return redirect(f"{base_url}?toast=unify_error")

        try:
            with transaction.atomic():
                # 統一先・曲を移すAuthorについてもTOCTOU対策として再取得してから統一する
                plan = build_unify_name_plan(self.author, new_name)
                target = plan.target_author
                song_author_pairs = plan.song_author_pairs()
                source_authors = plan.affected_source_authors(song_author_pairs)

                # 統一で新たに加わる曲と区別するため、名前の変更により表示上の作者名が
                # 変わる曲（元々authorに紐づいている曲）を移動前に確定させておく（#1034）
                renamed_song_ids = list(self.author.songs.values_list("id", flat=True)) if plan.renames_author else []

                author_infos = {a.pk: f"id={a.id}, name={a.name}" for a in plan.source_authors}
                target_info = f"id={target.id}, name={new_name}"
                source_infos_by_song_id = {}
                for song_id, author_id in song_author_pairs:
                    source_infos_by_song_id.setdefault(song_id, []).append(author_infos[author_id])

                if source_infos_by_song_id:
                    # 曲数が増えてもクエリ数が変わらないよう、idでまとめて付け替える
                    target.songs.add(*source_infos_by_song_id)
                    Song.authors.through.objects.filter(author__in=plan.source_authors).delete()

                if plan.moves_to_existing_author:
                    # 選択された側のAuthorAlias行は統一先自身の名前と同じになるため削除する
                    selected_alias.delete()
                    # グループ名は(name, author)単位でユニークなため、統一先が既に持つものは移さずに削除する
                    target_group_names = list(
                        AuthorAlias.objects.filter(author=target, alias_type="group").values_list("name", flat=True)
                    )
                    AuthorAlias.objects.filter(author=self.author, alias_type="group", name__in=target_group_names).delete()
                    AuthorAlias.objects.filter(author=self.author).update(author=target)
                    AuthorLink.objects.filter(author=self.author).update(author=target)
                elif plan.renames_author:
                    # 選択された側のAuthorAlias行は、これからauthor自身の名前になるため削除する
                    selected_alias.delete()
                    self.author.name = new_name
                    self.author.save()

                if old_name != new_name:
                    # 旧名を統一先の新たな「以前の名称」として登録し直す。統一先が既に
                    # 同名の別名を持つ場合は、新規作成せずその別名を再利用しつつ、他の
                    # past別名と同様に選択候補になるようalias_typeを"past"へ揃える
                    old_name_aliases = AuthorAlias.objects.filter(name=old_name)
                    if old_name_aliases.exclude(author=target).exists():
                        # send_discord()の待機中に、無関係な別authorがold_nameと同名の
                        # 別名を新規作成していた場合（TOCTOU）。他authorの別名を誤って
                        # 書き換えないよう、IntegrityErrorと同じ扱いで安全側に倒す
                        raise IntegrityError(f"AuthorAlias(name={old_name!r}) already exists and is not owned by the target author")
                    existing_old_alias = old_name_aliases.first()
                    if existing_old_alias is None:
                        AuthorAlias.objects.create(name=old_name, author=target, alias_type="past")
                    elif existing_old_alias.alias_type != "past":
                        existing_old_alias.alias_type = "past"
                        existing_old_alias.save()

                history_title = f"名義を『{new_name}』に統一"
                changes = [["種類", "編集前", "編集後"]]
                if plan.renames_author:
                    changes.append(["名義", old_name, new_name])
                for source in source_authors:
                    changes.append(["統一した作者", author_infos[source.pk], target_info])
                History.create_for_author(
                    author=target,
                    title=history_title,
                    history_type="edit",
                    changes=changes,
                    editor=editor,
                )
                # 曲を移したAuthorは削除されずに残るため、それぞれの編集履歴一覧にも統一先を記録する
                for source in source_authors:
                    History.create_for_author(
                        author=source,
                        title=history_title,
                        history_type="edit",
                        changes=[["種類", "編集前", "編集後"], ["統一した作者", author_infos[source.pk], target_info]],
                        editor=editor,
                    )

                # 統一により作者が変わった曲、名前の変更により作者の表示名が変わった曲
                # それぞれの編集履歴一覧にも記録する（#1034）。1回のbulk_create()でまとめて作成する。
                # 統一前から既にauthorと曲を移すAuthor双方に紐づいていた曲は、二重に記録しないよう
                # 統一側の文言のみで記録する
                now = timezone.now()
                song_histories = [
                    History(
                        song_id=song_id,
                        title="名義の統一により作者を統合",
                        history_type="edit",
                        create_time=now,
                        changes=[["種類", "編集前", "編集後"], ["作者", " / ".join(infos), target_info]],
                        editor=editor,
                    )
                    for song_id, infos in source_infos_by_song_id.items()
                ] + [
                    History(
                        song_id=song_id,
                        title="名義の統一により作者名を変更",
                        history_type="edit",
                        create_time=now,
                        changes=[["種類", "編集前", "編集後"], ["作者", old_name, new_name]],
                        editor=editor,
                    )
                    for song_id in renamed_song_ids
                    if song_id not in source_infos_by_song_id
                ]
                if song_histories:
                    History.objects.bulk_create(song_histories)
        except IntegrityError:
            # ほぼ同時に同名の別名が別途登録された場合等のTOCTOU対策
            return redirect(f"{base_url}?toast=unify_error")

        return redirect(f"{reverse('subekashi:author_aliases', args=[target.id])}?toast=unify")
