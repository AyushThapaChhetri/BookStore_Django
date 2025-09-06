from django.http import JsonResponse

from src.cart.models import CartItem


# Create your views here.
def cart_count_api(request):
    count = 0
    print('cart_count_api clicked')
    if request.user.is_authenticated:
        cart = CartItem.objects.filter(cart__user=request.user).count()
        count = cart
    print('cart Item', count)
    return JsonResponse({'count': count})
