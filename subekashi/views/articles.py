from django.shortcuts import render


def articles(request):
    return render(request, 'subekashi/articles.html')