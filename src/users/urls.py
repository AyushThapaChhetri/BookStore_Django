from src.users.views import UserCreateView, UserLoginView
from django.urls import path


urlpatterns=[
    path('signup/',UserCreateView.as_view(),name='signup_view'),
    path('login/',UserLoginView.as_view(),name='login_view'),
]