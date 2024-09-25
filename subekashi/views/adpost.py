from django.shortcuts import render


def adpost(request) :
    dataD = {
        "metatitle" : "申請完了",
    }
    return render(request, "subekashi/adpost.html", dataD)