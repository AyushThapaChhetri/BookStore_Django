"""
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from src.users.views import UserCreateView, UserLoginView, activate
from . import views
from .views import home_view, Dashboard

urlpatterns = [
                  # path('',views.home),
                  path('', home_view, name='home'),
                  path('admin/', admin.site.urls),
                  path('client/dashboard', Dashboard, name='client_dashboard'),
                  path('books/', include('src.books.urls')),
                  path('admin-panel/', include('src.books.admin_urls')),
                  path('admin-panel/', include('src.orders.admin_urls')),
                  path('admin-panel/', include('src.stock.admin_urls')),
                  path('users/', include('src.users.urls')),
                  path('carts/', include('src.cart.urls')),
                  path('delivery/', include('src.shipping.urls')),
                  path('orders/', include('src.orders.urls')),
                  path('about/', views.about_view, name='about_view'),
                  path('signup/', UserCreateView.as_view(), name='signup_view'),
                  path('login/', UserLoginView.as_view(), name='login_view'),
                  path('activate/<uidb64>/<token>/', activate, name='set_password_activate'),
                  path('reset_password/',
                       auth_views.PasswordResetView.as_view(template_name='users/password_reset_form.html'),
                       name='reset_password'),
                  path('reset_password_sent/',
                       auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
                       name='password_reset_done'),
                  path('reset/<uidb64>/<token>/',
                       auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
                       name='password_reset_confirm'),
                  path('reset_password_complete/',
                       auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
                       name='password_reset_complete'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + debug_toolbar_urls()

if settings.DEBUG:
    # Include django_browser_reload URLs only in DEBUG mode
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
