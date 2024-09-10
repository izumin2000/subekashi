from django.db.models import Q


def filter_by_category(queryset, category):
    return queryset.filter(
        Q(imitate=category) |
        Q(imitate__startswith=category + ',') |
        Q(imitate__endswith=',' + category) |
        Q(imitate__contains=',' + category + ',')
    )


islack = (
    ~Q(channel="全てあなたの所為です。") &
    (
        (Q(isdeleted=False) & Q(url="")) |
        (Q(isoriginal=False) & Q(issubeana=True) & Q(imitate="")) &
        (Q(isinst=False) & Q(lyrics=""))
    )
)