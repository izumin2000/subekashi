from django.db.models import Q


def include_keyword(keyword):
    return (
        Q(title__contains=keyword) |
        Q(channel__contains=keyword) |
        Q(lyrics__contains=keyword) |
        Q(url__contains=keyword)
    )
    
def include_imitate(imitate):
    imitate = str(imitate)
    return (
        Q(imitate=imitate) |
        Q(imitate__startswith=imitate + ',') |
        Q(imitate__endswith=',' + imitate) |
        Q(imitate__contains=',' + imitate + ',')
    )

def include_imitated(imitated):
    imitated = str(imitated)
    return (
        Q(imitated=imitated) |
        Q(imitated__startswith=imitated + ',') |
        Q(imitated__endswith=',' + imitated) |
        Q(imitated__contains=',' + imitated + ',')
    )

def include_guesser(guesser):
    return (
        Q(title__contains=guesser) |
        Q(channel__contains=guesser)
    )
    
include_youtube = Q(url__startswith="https://youtu.be/")

islack = (
    ~Q(channel="全てあなたの所為です。") &
    (
        (Q(isdeleted=False) & Q(url="")) |
        (Q(isoriginal=False) & Q(issubeana=True) & Q(imitate="")) &
        (Q(isinst=False) & Q(lyrics=""))
    )
)