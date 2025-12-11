from django.urls import path

from . import views
from .views import BookStore, BookCart, BookCheckout, BookCheckoutPayment, BookOrderComplete, \
    BookDetailStore

urlpatterns = [
   
    path('bookstore', BookStore.as_view(), name='book_store'),

    path('store/detail/<uuid>', BookDetailStore.as_view(), name='book_detail_store'),

    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<str:item_uuid>/', views.update_cart, name='update_cart'),
    path("cart/remove/<uuid:item_uuid>/", views.remove_cart_item, name="remove_cart_item"),
    path('cart/clear/', views.clear_cart, name='clear_cart'),

    # Checkout flow
    path('shopping-cart', BookCart.as_view(), name='book_cart'),
    path('checkout', BookCheckout.as_view(), name='book_checkout'),
    path('checkout/payment', BookCheckoutPayment.as_view(), name='book_payment'),
    path('checkout/order/complete', BookOrderComplete.as_view(), name='book_order_complete'),

    path('search/', views.search_books, name='search_books')
]
