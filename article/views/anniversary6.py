from django.shortcuts import render


def anniversary6(request) :
    images = ["graph_spring", "graph_random", "lyrics_default", "lyrics_icon", "lyrics_autumn", "lyrics_cool", "lyrics_rainbow", "lyrics_spring", "lyrics_summer", "lyrics_winter", "lyrics_Blues_r", "lyrics_BuGn_r", "lyrics_BuPu_r", "lyrics_GnBu_r", "lyrics_Greens_r", "lyrics_OrRd_r", "lyrics_Spectral_r"]
    dataD = {
        "metatitle": "6周年記念グラフィックアート",
        "images": images
    }
    return render(request, "article/anniversary6.html", dataD)