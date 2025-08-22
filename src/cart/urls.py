from django.urls import path

from src.cart import views

urlpatterns = [
    path('count/', views.cart_count_api)
]
