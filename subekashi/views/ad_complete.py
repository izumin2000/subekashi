from django.shortcuts import render


def ad_complete(request) :
    dataD = {
        "metatitle" : "申請完了",
    }
    return render(request, "subekashi/ad_complete.html", dataD)