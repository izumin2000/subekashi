from subekashi.models import Song
from subekashi.lib.filter import *

NUMBER_FORMS = ["view", "like", "post_time", "upload_time"]
NUMBER_GT_FORMS = [f"{column}_gt" for column in NUMBER_FORMS]
NUMBER_LT_FORMS = [f"{column}_lt" for column in NUMBER_FORMS]

PAGE_SIZE = 50

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
        
        # queryにNUMBER_FORM関係がある場合youtubeのurlを含むsongのみに絞る
        if len(set(query.keys()) & set(NUMBER_GT_FORMS + NUMBER_LT_FORMS)):
            song_qs = song_qs.filter(include_youtube)
        
        if query.get("islack"):
            song_qs = song_qs.filter(islack)
        
        if query.get("page"):
            page = int(query["page"])
            song_qs = song_qs[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        
    except Exception as e:
        return {"error": str(e)}
        
    return song_qs.order_by("-post_time")
    