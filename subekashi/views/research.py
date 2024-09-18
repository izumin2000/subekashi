from django.shortcuts import render


def research(request) :
    dataD = {
        "metatitle" : "研究",
    }
    return render(request, "subekashi/research.html", dataD)