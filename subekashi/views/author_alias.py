from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from subekashi.models import Author, AuthorAlias, Editor, History
from subekashi.forms import AuthorAliasForm
from subekashi.lib.ip import get_ip


LINKABLE_ALIAS_TYPES = ("past", "another")


class AuthorAliasesView(View):
    def get(self, request, author_id):
        author = Author.get_or_none(author_id)
        if author is None:
            return render(request, 'subekashi/404.html', status=404)

        effective_aliases = author.get_effective_aliases()

        # alias_typeがpast/anotherの別名のうち、実在するAuthorに対してのみchannelリンクを貼る
        linkable_names = set(
            Author.objects.filter(
                name__in=[ea.name for ea in effective_aliases if ea.alias_type in LINKABLE_ALIAS_TYPES]
            ).values_list("name", flat=True)
        )

        alias_rows = [
            {
                "name": ea.name,
                "alias_type_display": ea.alias_type_display,
                "is_reverse": ea.is_reverse,
                "alias_id": ea.source.id,
                "show_channel_link": ea.alias_type in LINKABLE_ALIAS_TYPES and ea.name in linkable_names,
            }
            for ea in effective_aliases
        ]

        context = {
            "metatitle": f"{author.name}の別名一覧",
            "author": author,
            "alias_rows": alias_rows,
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
            "alias_type_choices": AuthorAlias.CHOICES,
        }

    def get(self, request, author_id):
        return render(request, 'subekashi/author_alias_new.html', self.get_base_context())

    def post(self, request, author_id):
        context = self.get_base_context()
        form = AuthorAliasForm(request.POST, author=self.author)

        if not form.is_valid():
            context["error"] = list(form.errors.values())[0][0]
            return render(request, 'subekashi/author_alias_new.html', context)

        alias = AuthorAlias.objects.create(
            name=form.cleaned_data['name'],
            alias_type=form.cleaned_data['alias_type'],
            author=self.author,
        )

        editor = Editor.get_or_create_from_ip(get_ip(request))
        History.create_for_author(
            author=self.author,
            title=f"別名『{alias.name}』を追加",
            history_type="new",
            changes=[["種類", "内容"], ["別名", alias.name], ["種別", alias.get_alias_type_display()]],
            editor=editor,
        )

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
            "alias_type_choices": AuthorAlias.CHOICES,
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

        self.alias.name = form.cleaned_data['name']
        self.alias.alias_type = form.cleaned_data['alias_type']
        new_alias_type_display = self.alias.get_alias_type_display()

        changes = [["種類", "編集前", "編集後"]]
        if old_name != self.alias.name:
            changes.append(["別名", old_name, self.alias.name])
        if old_alias_type_display != new_alias_type_display:
            changes.append(["種別", old_alias_type_display, new_alias_type_display])

        self.alias.save()

        editor = Editor.get_or_create_from_ip(get_ip(request))
        History.create_for_author(
            author=self.author,
            title=f"別名『{old_name}』を編集",
            history_type="edit",
            changes=changes if len(changes) > 1 else None,
            editor=editor,
        )

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
        History.create_for_author(
            author=self.author,
            title=f"別名『{self.alias.name}』を削除",
            history_type="delete",
            changes=None,
            editor=editor,
        )

        self.alias.delete()

        return redirect(f"{reverse('subekashi:author_aliases', args=[self.author.id])}?toast=delete")
