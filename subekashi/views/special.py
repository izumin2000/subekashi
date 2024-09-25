from django.shortcuts import render


def special(request) :
    images = ["graph_spring", "graph_random", "lyrics_default", "lyrics_icon", "lyrics_autumn", "lyrics_cool", "lyrics_rainbow", "lyrics_spring", "lyrics_summer", "lyrics_winter", "lyrics_Blues_r", "lyrics_BuGn_r", "lyrics_BuPu_r", "lyrics_GnBu_r", "lyrics_Greens_r", "lyrics_OrRd_r", "lyrics_Spectral_r"]
    dataD = {
        "metatitle" : "スペシャル",
        "images": images
    }
    return render(request, "subekashi/special.html", dataD)