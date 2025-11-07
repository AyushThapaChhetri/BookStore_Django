from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView

from .models import Stock
from .services import update_stock_price


def update_price_view(request, stock_id):
    if request.method == "POST":
        stock = get_object_or_404(Stock, pk=stock_id)
        update_stock_price(
            stock,
            new_price=request.POST.get("price"),
            new_discount=request.POST.get("discount"),
            user=request.user,
            reason="Admin updated price"
        )
        return JsonResponse({"detail": "Stock updated successfully"})

    return JsonResponse({"error": "Only POST allowed"}, status=405)


# Create your views here.
class StockListView(ListView):
    model = Stock
    template_name = "books/admin/Stock/admin_stock_list.html"
    context_object_name = "stocks"


class StockDetailView(DetailView):
    model = Stock
    template_name = "books/admin/Stock/admin_stock_detail.html"
    context_object_name = "stock"
