from subekashi.models import Song
from subekashi.lib.filter import *
import math

DEFALT_SIZE = 50        # 1度の検索で取得できるsongオブジェクトの数

# 複数の検索条件があるクエリとそのフィルターの辞書
MULTI_FILTERS = {
    "keyword": filter_by_keyword,
    "imitate": filter_by_imitate,
    "imitated": filter_by_imitated,
    "guesser": filter_by_guesser,
    "islack": filter_by_lack,
}

# URLクエリの定数
TEXT_FORM = ["title", "channel", "lyrics", "url"]
YOUTUBE_ITEMS = ["view", "like", "upload_time"]
YOUTUBE_GTE_FORMS = [f"{item}_gte" for item in YOUTUBE_ITEMS]
YOUTUBE_LTE_FORMS = [f"{item}_lte" for item in YOUTUBE_ITEMS]
SORT_FORMS = ["sort"]
BOOL_FORMS = ["issubeana", "isjoke", "isdraft", "isoriginal", "isinst", "isdeleted"]
MULTI_FORMS = list(MULTI_FILTERS.keys())
INFO_ITEMS = ["page", "size", "count"]

# URLクエリの文字とfilterのルックアップの違いを示す変数
# 第1引数はqueryのカラム名
# 第2引数はURLクエリのカラムから削除する文字
# 第3引数はURLクエリのカラムの末尾に追加する文字
URL_QUERY_LOOKUP_DIFF = [
    (TEXT_FORM, "", "__icontains"),
    (YOUTUBE_GTE_FORMS, "_gte", "__gte"),
    (YOUTUBE_LTE_FORMS , "_lte", "__lte"),
    (BOOL_FORMS, "", ""),
]

# 全てのフォームを対象にしたURLクエリのキーをキーに、filterのルックアップを値にした辞書の生成
def get_song_filter():
    FLITER_DATA = {}
    for forms, delete_str, add_str in URL_QUERY_LOOKUP_DIFF:
        for form in forms:
            FLITER_DATA[form] = form.replace(delete_str, "") + add_str
    
    return FLITER_DATA

# クエリの値を整形
def clean_querys(querys):
    for item, value in querys.items():
        # クエリの値がリスト形式ならリストを取る
        if type(value) == list:
            value = value[0]
        
        # クエリのキーがbool型で値が真なら、値をTrueにする
        if (item in BOOL_FORMS) and (value in ["True", "true", 1]):
            value = True
            
        # クエリのキーがbool型で値が偽なら、値をFalseにする
        if (item in BOOL_FORMS) and (value in ["False", "false", 0]):
            value = False
    
        querys[item] = value
    return querys

# 複数の検索条件があるクエリをフィルタリング
def filter_multi_forms(querys, song_qs):
    for key, value in querys.items():
        if key == "islack":
            song_qs = song_qs.filter(filter_by_lack)
            continue
            
        # keyがislack以外の複数の検索条件があるクエリのkeyなら
        if key in MULTI_FORMS:
            filter_func = MULTI_FILTERS[key]
            song_qs = song_qs.filter(filter_func(value))
        
    return song_qs

# YouTubeに関するならurlに"youtu"を含ませる
def add_youtube_querys(querys):
    YOUTUBE_SORT = ["upload_time", "-upload_time", "view", "-view", "like", "-like"]
    has_youtube_sort = querys.get("sort") in YOUTUBE_SORT
    has_youtube_filter = len(set(YOUTUBE_GTE_FORMS + YOUTUBE_LTE_FORMS) & set(querys.keys())) > 0
    # YouTubeに関するソートではなかったら
    if not(has_youtube_sort or has_youtube_filter):
        return querys
    
    
    querys["url"] = "youtu"        # urlを"youtu"に上書きする
    print(querys)
    return querys
    
# URLクエリからfilterのルックアップに変換
def querys_to_single_filters(querys):
    filters = {}
    FORM_TYPE = get_song_filter()
    for item, value in querys.items():
        if item in INFO_ITEMS + SORT_FORMS + MULTI_FORMS:
            continue
            
        filters[FORM_TYPE[item]] = value
        
    return filters
    
# songの全カラム検索
def song_search(querys):
    querys = clean_querys(querys)
    statistics = {}
    
    # 条件が単数である条件を.filter(**
    querys = add_youtube_querys(querys)
    single_filters = querys_to_single_filters(querys)
    song_qs = Song.objects.filter(**single_filters)
    
    # 複数条件があるクエリを.filter
    song_qs = filter_multi_forms(querys, song_qs)

    # ソートの指示があればsong_qsを並び替え
    if querys.get("sort"):
        sort = querys["sort"]
        song_qs = song_qs.order_by("?" if sort == "random" else sort)

    # クエリ数をカウントする指示があればstatisticsに"count"を追加
    count = song_qs.count()
    if querys.get("count"):
        statistics["count"] = count
    
    # 1件もヒットしなかったら
    if not count:
        statistics["max_page"] = 1
        return Song.objects.none(), statistics
    
    # 表示個数の指示があったら検索結果を削る
    query_size = int(querys.get("size", 0))
    if (not querys.get("page")) and query_size:
        song_qs = song_qs[:query_size]
    
    # ページ数の指定があったら、そのページの検索結果を表示しその旨の統計を保存する
    if querys.get("page"):
        page = int(querys["page"])
        size = query_size if query_size else DEFALT_SIZE
        statistics["page"] = page
        statistics["size"] = size
        max_page = math.ceil(count / size)
        statistics["max_page"] = max_page
        if page > max_page:
            raise IndexError(f"最大ページ数{max_page}を超えています")
        song_qs = song_qs[(page - 1) * size : page * size]
        
    return song_qs, statistics
    