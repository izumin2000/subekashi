from django.shortcuts import render, redirect
from subekashi.models import *


def channel(request, channel_name):
    # Author.nameで検索し、存在すれば /author/<author_id>/ にリダイレクト
    try:
        author_obj = Author.objects.get(name=channel_name)
        return redirect('subekashi:author', author_id=author_obj.id)
    except Author.DoesNotExist:
        # 存在しない場合は404
        # get_object_or_404を使って404を返す
        return render(request, 'subekashi/404.html', status=404)