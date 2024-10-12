from subekashi.models import Song
from subekashi.lib.filter import *
import math

# TODO 定数をconstantsに移動
NUMBER_FORMS = ["view", "like", "post_time", "upload_time"]
NUMBER_GT_FORMS = [f"{column}_gt" for column in NUMBER_FORMS]
NUMBER_LT_FORMS = [f"{column}_lt" for column in NUMBER_FORMS]

LIB_FILTERS = {
    "keyword": include_keyword,
    "imitate": include_imitate,
    "imitated": include_imitated,
    "guesser": include_guesser,
    "youtube": include_youtube,
    "islack": islack,
}

DEFALT_SIZE = 50

# タプルの第1引数はqueryのカラム名、第2引数はobject.filterで使うField lookups
FORM_TYPE = {
    "text": (["title", "channel", "lyrics", "url"], "__icontains"),
    "number_gt": (NUMBER_GT_FORMS , "__gte"),
    "number_lt": (NUMBER_LT_FORMS , "__lte"),
    "bool": (["issubeana", "isjoke", "isdraft", "isoriginal", "isinst"], "")
}

# 各queryのカラムとそれに対応するField lookupsを記した辞書の生成
def get_song_filter():
    FLITER_DATA = {}
    for type, (columns, lookup) in FORM_TYPE.items():
        for column in columns:
            filter = column
            if type in ["number_gt", "number_lt"]:      # number関係は以上・以下を示す_gt・_ltを消す
                filter = column.replace("_gt", "").replace("_lt", "")
            FLITER_DATA[column] = filter + lookup
    
    return FLITER_DATA

def clean_query(query):
    for column, value in query.items():
        if type(value) == list:
            value = value[0]
        
        if column.startswith("is") and (value in ["True", "true", 1]):
            value = True
            
        if column.startswith("is") and (value in ["False", "false", 0]):
            value = False
    
        query[column] = value
    return query

def query_to_filters(query):
    filters = {}
    FORM_TYPE = get_song_filter()
    
    for column, value in query.items():
        if not FORM_TYPE.get(column):       # Songカラムに無いqueryは無視
            continue
        
        filters.update({FORM_TYPE[column]: value})
        
    return filters
    
# songの全カラム検索
def song_search(query):
    query = clean_query(query)
    filters = query_to_filters(query)
    statistics = {}
    
    try:
        song_qs = Song.objects.filter(**filters)

        for key, filter_func in LIB_FILTERS.items():
            # NUMBER_FORMかソートがある場合youtubeのurlを含むsongのみに絞る
            if key == "youtube":
                has_number_form = len(set(query.keys()) & set(NUMBER_GT_FORMS + NUMBER_LT_FORMS)) >= 1
                if has_number_form:
                    song_qs = song_qs.filter(include_youtube)
                continue
            
            if (key in query) and (key == "islack"):
                song_qs = song_qs.filter(islack)
                continue
            
            if key in query:
                value = query[key]
                song_qs = song_qs.filter(filter_func(value))
        
        if "sort" in query:
            sort = query["sort"]
            if sort in ["upload_time", "-upload_time"]:
                song_qs = song_qs.filter(upload_time__isnull = False)
            if sort in ["view", "-view"]:
                song_qs = song_qs.filter(view__gt = 0)
            if sort in ["like", "-like"]:
                song_qs = song_qs.filter(like__gt = 0)
            if sort == "random":
                sort = "?"
            song_qs = song_qs.order_by(sort)

        count = song_qs.count()
        if "count" in query:
            statistics["count"] = count
        
        if not count:
            statistics["max_page"] = 1
            return Song.objects.none(), statistics
        
        query_size = int(query.get("size", 0))
        if "page" not in query and query_size:
            song_qs = song_qs[:query_size]
            
        if "page" in query:
            page = int(query["page"])
            size = query_size if query_size else DEFALT_SIZE
            statistics["page"] = page
            statistics["size"] = size
            max_page = math.ceil(count / size)
            statistics["max_page"] = max_page
            if page > max_page:
                raise IndexError(f"最大ページ数{max_page}を超えています")
            song_qs = song_qs[(page - 1) * size : page * size]
        
    except Exception as e:
        return {"error": str(e)}
    
    return song_qs, statistics
    