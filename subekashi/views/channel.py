from django.shortcuts import render, redirect
from django.views import View
from subekashi.models import Author


class ChannelView(View):
    def get(self, request, channel_name):
        # Author.nameで検索し、存在すれば /author/<author_id>/ にリダイレクト
        author_obj = Author.get_by_name(channel_name)
        if author_obj is not None:
            return redirect('subekashi:author', author_id=author_obj.id)
        return render(request, 'subekashi/404.html', status=404)
