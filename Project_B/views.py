from django.shortcuts import render

from src.cart.models import Cart, CartItem


def home_view(request):
    cart = None
    items_count = 0

    # print('from home')
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            items_count = CartItem.objects.filter(cart=cart).count()

    # print('about to render')
    # messages.success(request, 'You have been logged in.')
    return render(request, 'base/base.html', {
        'cart': cart,
        'items_count': items_count
    })

    #
    #     return render(request, 'base/base.html', {'cart': cart, 'items_count': items_count})
    # return render(request, 'base/base.html')


def Dashboard(request):
    return render(request, 'dashboard/client/base_dashboard.html')


def about_view(request):
    return render(request, 'about/aboutpage.html')
