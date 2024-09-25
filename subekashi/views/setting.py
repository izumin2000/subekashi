from django.shortcuts import render


def setting(request) :
    dataD = {
        "metatitle" : "設定",
    }
    return render(request, "subekashi/setting.html", dataD)