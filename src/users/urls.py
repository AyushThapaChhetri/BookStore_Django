from django.urls import path

from src.users.views import UserLogoutView

urlpatterns = [
    # path('signup/',UserCreateView.as_view(),name='signup_view'),
    # path('login/',UserLoginView.as_view(),name='login_view'),
    path('logout/', UserLogoutView.as_view(), name='logout_view'),
]
