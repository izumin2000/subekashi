from django.shortcuts import render
from subekashi.lib.ip import get_ip
from subekashi.models import Editor


def setting(request):
    ip = get_ip(request)
    editor, _ = Editor.objects.get_or_create(ip = ip)

    settings_data = {
        'top': [
            {
                'label': '界隈曲の表示',
                'id': 'songrange',
                'options': [
                    {'value': 'all', 'text': '全て表示', 'selected': False},
                    {'value': 'subeana', 'text': 'すべあな界隈曲のみを表示', 'selected': True},
                    {'value': 'xx', 'text': 'すべあな界隈曲以外を表示', 'selected': False},
                ]
            },
            {
                'label': 'ネタ曲の表示',
                'id': 'jokerange',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': False},
                    {'value': 'off', 'text': '非表示', 'selected': True},
                ]
            },
            {
                'label': 'ニュースの表示',
                'id': 'news_type',
                'options': [
                    {'value': 'single', 'text': '1つずつ表示', 'selected': True},
                    {'value': 'all', 'text': '一度に全て表示', 'selected': True},
                    {'value': 'off', 'text': '非表示', 'selected': False},
                ]
            },
            {
                'label': '検索の表示',
                'id': 'is_shown_search',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': True},
                    {'value': 'off', 'text': '非表示', 'selected': False},
                ]
            },
            {
                'label': '新着の表示',
                'id': 'is_shown_new',
                'options': [
                    {'value': 15, 'text': '15曲表示', 'selected': False},
                    {'value': 10, 'text': '10曲表示', 'selected': False},
                    {'value': 5, 'text': '5曲表示', 'selected': True},
                    {'value': 0, 'text': '非表示', 'selected': False},
                ]
            },
            {
                'label': '宣伝の表示',
                'id': 'is_shown_ad',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': True},
                    {'value': 'off', 'text': '非表示', 'selected': False},
                ]
            },
            {
                'label': '生成された歌詞の表示',
                'id': 'is_shown_ai',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': True},
                    {'value': 'off', 'text': '非表示', 'selected': False},
                ]
            },
            {
                'label': '未完成の表示',
                'id': 'is_shown_lack',
                'options': [
                    {'value': 15, 'text': '15曲表示', 'selected': False},
                    {'value': 10, 'text': '10曲表示', 'selected': False},
                    {'value': 5, 'text': '5曲表示', 'selected': True},
                    {'value': 0, 'text': '非表示', 'selected': False},
                ]
            },
        ],
        'search': [
            {
                'label': '検索の選択肢の保存',
                'id': 'is_saved_select',
                'options': [
                    {'value': 'on', 'text': '保存', 'selected': True},
                    {'value': 'off', 'text': '未保存', 'selected': False},
                ]
            },
        ],
        'song': [
            {
                'label': '歌詞の改行',
                'id': 'brlyrics',
                'options': [
                    {'value': 'normal', 'text': '全ての改行を表示', 'selected': True},
                    {'value': 'pack', 'text': '連続した改行を非表示', 'selected': False},
                    {'value': 'brless', 'text': '全ての改行を非表示', 'selected': False},
                ]
            },
        ],
        'edit': [
            {
                'label': '編集の公開',
                'id': 'is_open',
                'options': [
                    {'value': 'on', 'text': '公開', 'selected': editor.is_open},
                    {'value': 'off', 'text': '非公開', 'selected': not editor.is_open},
                ]
            },
        ],
    }

    dataD = {
        "metatitle": "設定",
        "editor": editor,
        "settings": settings_data,
    }
    return render(request, "subekashi/setting.html", dataD)