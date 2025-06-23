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
    "mediatypes": filter_by_mediatypes,
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
EXACT_ITEMS = ["title_exact", "channel_exact"]
ALL_QUERYS = TEXT_FORM + YOUTUBE_GTE_FORMS + YOUTUBE_LTE_FORMS + SORT_FORMS + BOOL_FORMS + MULTI_FORMS + INFO_ITEMS + EXACT_ITEMS

# 1つの条件を指定しているキー名とfilterのルックアップの違いを示す変数
# 第1引数は対象となるクエリのキー名のリスト
# 第2引数はキー名から削除する文字
# 第3引数はキー名の末尾に追加する文字
SINGLE_QUERY_LOOKUP_DIFF = [
    (TEXT_FORM, "", "__icontains"),
    (YOUTUBE_GTE_FORMS, "_gte", "__gte"),
    (YOUTUBE_LTE_FORMS , "_lte", "__lte"),
    (BOOL_FORMS, "", ""),
    (EXACT_ITEMS, "_exact", ""),
]

# クエリの値を整形
def clean_querys(querys):
    cleand_querys = {}
    for item, value in querys.items():
        # 不必要なクエリを削除
        if item not in ALL_QUERYS:
            continue
        
        # クエリの値がリスト形式ならリストを取る
        if type(value) == list:
            value = value[0]
        
        # クエリのキーがbool型で値が真なら、値をTrueにする
        if (item in BOOL_FORMS) and (value in ["True", "true", 1]):
            value = True
            
        # クエリのキーがbool型で値が偽なら、値をFalseにする
        if (item in BOOL_FORMS) and (value in ["False", "false", 0]):
            value = False
    
        cleand_querys[item] = value
    return cleand_querys

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
    return querys

# クエリのうち単数条件のクエリを対象にしたクエリのキーをキーに、filterのルックアップを値にした辞書を生成
def create_single_filter_dict():
    single_filter_dict = {}
    for forms, delete_str, add_str in SINGLE_QUERY_LOOKUP_DIFF:
        for form in forms:
            single_filter_dict[form] = form.replace(delete_str, "") + add_str
    return single_filter_dict
    
# クエリのうち単数条件のクエリをfilterのルックアップに変換
def querys_to_single_filters(querys):
    single_filters = {}
    single_filter_dict = create_single_filter_dict()
    for item, value in querys.items():
        if item in INFO_ITEMS + SORT_FORMS + MULTI_FORMS:
            continue

        single_filters[single_filter_dict[item]] = value
        
    return single_filters
    
# songのフィルタリング・ソート・統計
def song_search(querys):
    querys = clean_querys(querys)
    statistics = {}
    
    # 条件が1つである条件を.filter(**
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
    
    # ページ数の指定があったら、そのページの検索結果を表示しその旨の統計を保存する
    if querys.get("page"):
        page = int(querys["page"])
        size = int(querys.get("size", DEFALT_SIZE))
        statistics["page"] = page
        statistics["size"] = size
        max_page = math.ceil(count / size)
        statistics["max_page"] = max_page
        song_qs = song_qs[(page - 1) * size : page * size]
        
    return song_qs, statistics