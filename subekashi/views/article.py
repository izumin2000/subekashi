from django.shortcuts import render


def article(request, article_id):
    return render(request, 'subekashi/article.html')