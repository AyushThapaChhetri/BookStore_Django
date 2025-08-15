from django.urls import path

from . import views
from .views import BookListView, BookDetailView, BookView, BookStore, BookCart, BookCheckout, BookCheckoutPayment, \
    BookOrderComplete, BookDetailStore

urlpatterns = [
    path('hello', views.hello),
    path('list', BookListView.as_view(), name='book_list'),
    path('bookstore', BookStore.as_view(), name='book_store'),

    # Specific actions for books
    path('', BookView.as_view(), name='book_view'),
    path('edit/<uuid>', BookView.as_view(), name='book_view'),
    path('delete/<uuid>', BookView.as_view(), name='book_delete'),
    path('store/detail/<uuid>', BookDetailStore.as_view(), name='book_detail_store'),
    path('detail/<uuid>', BookDetailView.as_view(), name='book_detail_view'),

    # Checkout flow
    path('shopping-cart', BookCart.as_view(), name='book_cart'),
    path('checkout', BookCheckout.as_view(), name='book_checkout'),
    path('checkout/payment', BookCheckoutPayment.as_view(), name='book_payment'),
    path('checkout/order/complete', BookOrderComplete.as_view(), name='book_order_complete'),

    path('search/', views.search_books, name='search_books')
]
