from django.shortcuts import render

from src.cart.models import Cart, CartItem


def home_view(request):
    cart = None
    items_count = 0
    
    if request.user.is_authenticated:
        cart = Cart.objects.get(user=request.user)
        items_count = CartItem.objects.filter(cart=cart).count()
    return render(request, 'base/base.html', {'cart': cart, 'items_count': items_count})


def about_view(request):
    return render(request, 'about/aboutpage.html')
