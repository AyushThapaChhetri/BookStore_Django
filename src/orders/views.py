from django.shortcuts import render
from django.views import View

from src.orders.models import Order, OrderItem


# Create your views here.
class MyOrders(View):
    def get(self, request):
        print('myorders')
        # Get all orders of the logged-in user
        user_orders = Order.objects.filter(user=request.user).prefetch_related('items', 'items__book')
        # print("User Orders:", user_orders)

        # Get all order items of the logged-in user (if you need them separately)
        user_order_items = OrderItem.objects.filter(order__user=request.user).select_related('order', 'book')
        # print("User Order Items:", user_order_items)

        return render(request, 'orders/myorder_dashboard.html', {
            "orders": user_orders,
            "order_items": user_order_items,
        })
