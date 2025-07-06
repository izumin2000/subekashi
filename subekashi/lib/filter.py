from django.db.models import Q
from subekashi.constants.constants import ALL_MEDIAS

# topやsearchにあるキーワード検索のフィルター
def filter_by_keyword(keyword):
    return (
        Q(title__contains = keyword) |
        Q(channel__contains = keyword) |
        Q(lyrics__contains = keyword) |
        Q(url__contains = keyword)
    )

# 模倣のフィルター
def filter_by_imitate(imitate):
    imitate = str(imitate)
    return (
        Q(imitate = imitate) |
        Q(imitate__startswith = imitate + ',') |
        Q(imitate__endswith = ',' + imitate) |
        Q(imitate__contains = ',' + imitate + ',')
    )

# 被模倣のフィルター
def filter_by_imitated(imitated):
    imitated = str(imitated)
    return (
        Q(imitated = imitated) |
        Q(imitated__startswith = imitated + ',') |
        Q(imitated__endswith = ',' + imitated) |
        Q(imitated__contains = ',' + imitated + ',')
    )

# 模倣曲の検索に利用するフィルター
def filter_by_guesser(guesser):
    return (
        Q(title__contains = guesser) |
        Q(channel__contains = guesser)
    )

# メディアの検索に利用するフィルター
def filter_by_mediatypes(mediatypes):
    # mediatypeに当てはまる正規表現を抜き出す
    media_regex_list = []
    for mediatype in mediatypes.split(","):
        for i, media in enumerate(ALL_MEDIAS):
            if mediatype == media["name"]:
                media_regex_list.append(f"({ALL_MEDIAS[i]['regex']})")
                continue
    media_regex = "|".join(media_regex_list)
    return (
        Q(url__regex = media_regex)
    )

# 未完成フィルター
filter_by_lack = (
    (Q(isdeleted = False) & Q(url = "")) |
    (Q(isoriginal = False) & Q(issubeana = True) & Q(imitate = "") & ~Q(channel = "全てあなたの所為です。")) | 
    (Q(isinst = False) & Q(lyrics = ""))
)

# 未完成かどうか
def is_lack(song):
    if (song.isdeleted == False) and (song.url == ""):
        return True
    
    if (song.isoriginal == False) and (song.issubeana == False) and (song.imitate == "") and (song.channel == "全てあなたの所為です。"):
        return True
    
    if (song.isinst == False) and (song.lyrics == ""):
        return True
    
    return False   
        