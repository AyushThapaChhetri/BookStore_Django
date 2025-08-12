from django.shortcuts import render


def home_view(request):
    return render(request, 'base/base.html')


def about_view(request):
    return render(request, 'about/aboutpage.html')
