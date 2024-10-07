from subekashi.models import Song
from subekashi.lib.filter import *
import math

NUMBER_FORMS = ["view", "like", "post_time", "upload_time"]
NUMBER_GT_FORMS = [f"{column}_gt" for column in NUMBER_FORMS]
NUMBER_LT_FORMS = [f"{column}_lt" for column in NUMBER_FORMS]

DEFALT_PAGE_SIZE = 50

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

# songの全カラム検索
def song_search(query):
    FORM_TYPE = get_song_filter()
    
    filters = {}
    statistics = {}
    query = {value: key[0] for value, key in query.items()}
    for column, value in query.items():
        if not FORM_TYPE.get(column):       # Songカラムに無いqueryは無視
            continue
        
        filters.update({FORM_TYPE[column]: value})
    
    try :
        song_qs = Song.objects.filter(**filters)
        
        if query.get("keyword"):
            song_qs = song_qs.filter(include_keyword(query["keyword"]))
            
        if query.get("imitate"):
            song_qs = song_qs.filter(include_imitate(query["imitate"]))
        
        if query.get("imitated"):
            song_qs = song_qs.filter(include_imitated(query["imitated"]))
        
        # NUMBER_FORMかソートがある場合、youtubeのurlを含むsongのみに絞る
        has_number_form = len(set(query.keys()) & set(NUMBER_GT_FORMS + NUMBER_LT_FORMS)) >= 1
        has_sort = query.get("sort", False)
        if has_number_form or has_sort:
            song_qs = song_qs.filter(include_youtube)
        
        if query.get("islack"):
            song_qs = song_qs.filter(islack)
        
        if query.get("sort"):
            song_qs = song_qs.order_by(query["sort"])
        
        count = song_qs.count()
        statistics["count"] = count
        if query.get("page"):
            page = int(query["page"])
            page_size = int(query["page_size"]) if query.get("page_size") else DEFALT_PAGE_SIZE
            statistics["page"] = page
            statistics["page_size"] = page_size
            max_page = math.ceil(count/page_size)
            statistics["max_page"] = max_page
            if page > max_page:
                raise IndexError(f"最大ページ数{max_page}を超えています")
            song_qs = song_qs[(page - 1) * page_size : page * page_size]
        
    except Exception as e:
        return {"error": str(e)}
    
    
    return song_qs, statistics
    