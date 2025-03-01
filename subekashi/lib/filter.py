from django.db.models import Q


def filter_by_keyword(keyword):
    return (
        Q(title__contains=keyword) |
        Q(channel__contains=keyword) |
        Q(lyrics__contains=keyword) |
        Q(url__contains=keyword)
    )
    
def filter_by_imitate(imitate):
    imitate = str(imitate)
    return (
        Q(imitate=imitate) |
        Q(imitate__startswith=imitate + ',') |
        Q(imitate__endswith=',' + imitate) |
        Q(imitate__contains=',' + imitate + ',')
    )

def filter_by_imitated(imitated):
    imitated = str(imitated)
    return (
        Q(imitated=imitated) |
        Q(imitated__startswith=imitated + ',') |
        Q(imitated__endswith=',' + imitated) |
        Q(imitated__contains=',' + imitated + ',')
    )

def filter_by_guesser(guesser):
    return (
        Q(title__contains=guesser) |
        Q(channel__contains=guesser)
    )
    
filter_by_lack = (
    (Q(isdeleted=False) & Q(url="")) |
    (Q(isoriginal=False) & Q(issubeana=True) & Q(imitate="") & ~Q(channel="全てあなたの所為です。")) | 
    (Q(isinst=False) & Q(lyrics=""))
)