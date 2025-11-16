import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.views import View

from Project_B.utils import applying_sorting, ALLOWED_SORTS
from src.books.pagination import paginate_queryset
from src.orders.models import Order, OrderItem
from src.orders.utils import search_order
from src.stock.services import StockService


@login_required
def update_order_status(request, order_id):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'})

    order = get_object_or_404(Order, id=order_id)

    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    try:
        data = json.loads(request.body)
        new_status = data.get('status')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid data'})

    print("Status: ", new_status)
    if order.status in ['completed', 'cancelled']:
        return JsonResponse({'success': False, 'message': f'Order is already {order.get_status_display()}'})

    if new_status not in dict(Order.STATUS_CHOICES):
        return JsonResponse({'success': False, 'message': 'Invalid status selected'})

    print("hello")
    try:
        with transaction.atomic():
            if new_status == "completed":
                print("completed")
                for item in order.items.all():
                    StockService.finalize_reservation(item, changed_by=request.user)
            if new_status == "cancelled":
                print("cancelled")
                for item in order.items.all():
                    StockService.release_reservation(item, changed_by=request.user)

            print("before completion")
            order.status = new_status
            order.save(update_fields=['status'])

    except Exception as e:
        print(e)
        print("Error updating order:", e)
        return JsonResponse({'success': False, 'message': 'Error while updating order. Try again.'})

    # messages.success(request, 'Order status updated')

    # order.status = new_status
    # order.save(update_fields=['status'])

    return JsonResponse({'success': True, 'new_status': order.get_status_display()})


class MyOrders(View):
    def get(self, request):
        # print('myorders')

        user_orders = Order.objects.filter(user=request.user).prefetch_related('items', 'items__book').order_by(
            '-created_at')
        # print("User Orders:", user_orders)

        user_order_items = OrderItem.objects.filter(order__user=request.user).select_related('order', 'book')
        # print("User Order Items:", user_order_items)
        if not request.user.is_superuser:
            print("not superuser")
            return render(request, 'orders/myorder_dashboard.html', {
                "orders": user_orders,
                "order_items": user_order_items,
            })

        print("superuser")
        return render(request, 'orders/admin/admin_order_dashboard.html', {
            "orders": user_orders,
            "order_items": user_order_items,
        })


class OrderView(View):
    def get(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            print("not superuser")
            messages.error(request, "You are not authorized to view this page.")
            return redirect('home')

        sort_by = request.GET.get('sort')
        show_by = request.GET.get('showby')
        query = request.GET.get('q', '')

        order = Order.objects.all().select_related('user')
        # print("order: ", order)
        if query:
            order = search_order(order, query)

        # print("query: ", query)
        # print("query: ", order)

        if show_by in dict(Order.STATUS_CHOICES):
            order = order.filter(status=show_by)

        sorted_order = applying_sorting(order, sort_by=sort_by, allowed_sorts=ALLOWED_SORTS["order"],
                                        default='-created_at')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get(
                'Accept') == 'application/json':
            data = [
                {
                    "id": order.id,
                    "uuid": str(order.uuid),
                    "user_email": order.user.email if order.user else None,
                    "total_amount": str(order.total_amount),
                    "order_date": order.order_date.isoformat() if order.order_date else None,
                    "status": order.status,
                    "status_choices": Order.STATUS_CHOICES,
                }
                for order in sorted_order
            ]
            print(' response')
            return JsonResponse({"orders": data}, safe=False)

        paginated_order, limit = paginate_queryset(request, sorted_order, default_limit=10)

        return render(request, 'orders/admin/admin_order_dashboard.html', {
            'paginated_order': paginated_order,
            'limit': limit})


class Order_detail_view(View):
    def get(self, request, order_uuid):
        order = get_object_or_404(
            Order.objects.prefetch_related("items__book", "user"),
            uuid=order_uuid
        )

        return render(request, "orders/admin/admin_order_detail.html", {
            "order": order,
            "items": order.items.all()
        })
