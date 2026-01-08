from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from subekashi.lib.ip import get_ip
from subekashi.models import Editor
from subekashi.constants.constants import LONG_TERM_COKKIE_AGE
import json


def setting(request):
    ip = get_ip(request)
    editor, _ = Editor.objects.get_or_create(ip = ip)

    # 現在のcookie値を取得
    songrange = request.COOKIES.get("songrange", "subeana")
    jokerange = request.COOKIES.get("jokerange", "off")
    news_type = request.COOKIES.get("news_type", "single")
    is_shown_search = request.COOKIES.get("is_shown_search", "on")
    is_shown_new = request.COOKIES.get("is_shown_new", "5")
    is_shown_ad = request.COOKIES.get("is_shown_ad", "on")
    is_shown_ai = request.COOKIES.get("is_shown_ai", "on")
    is_shown_lack = request.COOKIES.get("is_shown_lack", "5")
    is_saved_select = request.COOKIES.get("is_saved_select", "on")
    brlyrics = request.COOKIES.get("brlyrics", "normal")

    settings_data = {
        'top': [
            {
                'label': '界隈曲の表示',
                'id': 'songrange',
                'options': [
                    {'value': 'all', 'text': '全て表示', 'selected': songrange == 'all'},
                    {'value': 'subeana', 'text': 'すべあな界隈曲のみを表示', 'selected': songrange == 'subeana'},
                    {'value': 'xx', 'text': 'すべあな界隈曲以外を表示', 'selected': songrange == 'xx'},
                ]
            },
            {
                'label': 'ネタ曲の表示',
                'id': 'jokerange',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': jokerange == 'on'},
                    {'value': 'off', 'text': '非表示', 'selected': jokerange == 'off'},
                ]
            },
            {
                'label': 'ニュースの表示',
                'id': 'news_type',
                'options': [
                    {'value': 'single', 'text': '1つずつ表示', 'selected': news_type == 'single'},
                    {'value': 'all', 'text': '一度に全て表示', 'selected': news_type == 'all'},
                    {'value': 'off', 'text': '非表示', 'selected': news_type == 'off'},
                ]
            },
            {
                'label': '検索の表示',
                'id': 'is_shown_search',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': is_shown_search == 'on'},
                    {'value': 'off', 'text': '非表示', 'selected': is_shown_search == 'off'},
                ]
            },
            {
                'label': '新着の表示',
                'id': 'is_shown_new',
                'options': [
                    {'value': '15', 'text': '15曲表示', 'selected': is_shown_new == '15'},
                    {'value': '10', 'text': '10曲表示', 'selected': is_shown_new == '10'},
                    {'value': '5', 'text': '5曲表示', 'selected': is_shown_new == '5'},
                    {'value': '0', 'text': '非表示', 'selected': is_shown_new == '0'},
                ]
            },
            {
                'label': '宣伝の表示',
                'id': 'is_shown_ad',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': is_shown_ad == 'on'},
                    {'value': 'off', 'text': '非表示', 'selected': is_shown_ad == 'off'},
                ]
            },
            {
                'label': '生成された歌詞の表示',
                'id': 'is_shown_ai',
                'options': [
                    {'value': 'on', 'text': '表示', 'selected': is_shown_ai == 'on'},
                    {'value': 'off', 'text': '非表示', 'selected': is_shown_ai == 'off'},
                ]
            },
            {
                'label': '未完成の表示',
                'id': 'is_shown_lack',
                'options': [
                    {'value': '15', 'text': '15曲表示', 'selected': is_shown_lack == '15'},
                    {'value': '10', 'text': '10曲表示', 'selected': is_shown_lack == '10'},
                    {'value': '5', 'text': '5曲表示', 'selected': is_shown_lack == '5'},
                    {'value': '0', 'text': '非表示', 'selected': is_shown_lack == '0'},
                ]
            },
        ],
        'search': [
            {
                'label': '検索の選択肢の保存',
                'id': 'is_saved_select',
                'options': [
                    {'value': 'on', 'text': '保存', 'selected': is_saved_select == 'on'},
                    {'value': 'off', 'text': '未保存', 'selected': is_saved_select == 'off'},
                ]
            },
        ],
        'song': [
            {
                'label': '歌詞の改行',
                'id': 'brlyrics',
                'options': [
                    {'value': 'normal', 'text': '全ての改行を表示', 'selected': brlyrics == 'normal'},
                    {'value': 'pack', 'text': '連続した改行を非表示', 'selected': brlyrics == 'pack'},
                    {'value': 'brless', 'text': '全ての改行を非表示', 'selected': brlyrics == 'brless'},
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


@require_http_methods(["POST"])
def save_settings(request):
    """
    設定画面のcookieを保存するバックエンドエンドポイント
    """
    try:
        data = json.loads(request.body)
        cookies = data.get('cookies', {})

        # レスポンスを作成
        response = JsonResponse({'status': 'success', 'message': '設定を保存しました'})

        # 各cookieを設定 (365日間有効)
        for key, value in cookies.items():
            response.set_cookie(
                key=key,
                value=str(value),
                max_age=LONG_TERM_COKKIE_AGE,
                path='/',
                samesite='Lax'
            )

        return response

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)