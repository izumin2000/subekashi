from django.views.generic import TemplateView


class Anniversary6View(TemplateView):
    template_name = "article/anniversary6.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metatitle"] = "6周年記念グラフィックアート"
        context["images"] = ["graph_spring", "graph_random", "lyrics_default", "lyrics_icon", "lyrics_autumn", "lyrics_cool", "lyrics_rainbow", "lyrics_spring", "lyrics_summer", "lyrics_winter", "lyrics_Blues_r", "lyrics_BuGn_r", "lyrics_BuPu_r", "lyrics_GnBu_r", "lyrics_Greens_r", "lyrics_OrRd_r", "lyrics_Spectral_r"]
        return context
