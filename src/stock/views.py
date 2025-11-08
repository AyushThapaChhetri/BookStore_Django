from django.contrib.auth.decorators import login_required
# src/books/views.py (add/update these)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import RestockForm, PriceUpdateForm  # From Step 3
from .models import Book
from .models import StockReservation
from .services import StockService


@login_required
def stock_detail(request, book_uuid):
    # print("stock detail page")
    book = get_object_or_404(Book, uuid=book_uuid)
    stock = book.stock
    if not request.user.is_staff:
        return redirect('book_detail_store', book_uuid)

    # batches = stock.batches.all()
    batches = stock.batches.order_by('received_date', 'created_at')[:10]
    # for batch in batches:
    #     print(batch.received_date)
    #     print(batch.created_at)
    history = stock.stock_history.order_by('-created_at')[:10]
    price_history = stock.price_history.order_by('-created_at')[:5]
    reservations = StockReservation.objects.filter(batch__stock=stock, is_active=True)

    context = {
        'book': book,
        'stock': stock,
        'batches': batches,
        'history': history,
        'price_history': price_history,
        'reservations': reservations,
    }
    # print("stock detail page")
    return render(request, 'books/admin/Stock/admin_stock_detail_view.html', context)


@login_required
def restock(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    stock = book.stock
    if not request.user.is_staff:
        return redirect('book_detail_store', book_uuid)

    if request.method == 'POST':
        form = RestockForm(request.POST)
        if form.is_valid():
            # Use service (wraps your add_stock_batch)
            StockService.restock(
                stock=stock,
                initial_quantity=form.cleaned_data['initial_quantity'],
                unit_cost=form.cleaned_data['unit_cost'],
                received_date=form.cleaned_data['received_date'],
                notes=form.cleaned_data['notes'],
                user=request.user
            )
            return redirect('stock_detail', book_uuid)
    else:
        form = RestockForm(initial={'received_date': timezone.now().date()})

    return render(request, 'books/admin/Stock/admin_restock.html', {'form': form, 'book': book})


@login_required
def update_price(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    stock = book.stock

    if not request.user.is_staff:
        return redirect('book_detail_store', book_uuid)

    if request.method == 'POST':
        form = PriceUpdateForm(request.POST)
        if form.is_valid():
            # Use service (wraps your update_stock_price)

            StockService.update_price(
                stock=stock,
                new_price=form.cleaned_data['current_price'],
                new_discount=form.cleaned_data['current_discount_percentage'],
                user=request.user,
                reason=form.cleaned_data.get('reason', "Manual update")
            )
            return redirect('stock_detail', book_uuid)
    else:
        form = PriceUpdateForm(instance=stock)

    return render(request, 'books/admin/Stock/admin_update_price.html', {'form': form, 'book': book})
