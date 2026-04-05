from django.views.generic import TemplateView


class AdCompleteView(TemplateView):
    template_name = "subekashi/ad_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["metatitle"] = "申請完了"
        return context
