from django.contrib.auth.decorators import login_required
# src/books/views.py (add/update these)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import RestockForm, PriceUpdateForm  # From Step 3
from .models import Book
from .models import StockReservation
from .services import StockService
from ..books.pagination import paginate_queryset


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
    reservations = StockReservation.objects.filter(batch__stock=stock, is_active=True)[:10]

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
def stockBatchesView(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    batches = book.stock.batches.all().order_by('-received_date')
    paginated_batches, limit = paginate_queryset(request, batches, default_limit=10)
    return render(request, 'books/admin/Stock/admin_stock_batches.html', {
        'paginated_batches': paginated_batches,
        'limit': limit,
        'book': book,
        'headers': ['Date', 'Initial', 'Remaining', 'Cost', 'Supplier', 'Notes']
    })


@login_required
def stockHistoryView(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    stock_history = book.stock.stock_history.all().order_by('-created_at')
    paginated_stock_history, limit = paginate_queryset(request, stock_history, default_limit=10)
    return render(request, 'books/admin/Stock/admin_stock_history.html', {
        'paginated_stock_history': paginated_stock_history,
        'limit': limit,
        'book': book,
        'headers': ['Type', 'Change', 'Before', 'After', 'By', 'Date']
    })


@login_required
def stockPriceView(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    stock_price_history = book.stock.price_history.all().order_by('-created_at')
    print(stock_price_history)
    paginated_price_history, limit = paginate_queryset(request, stock_price_history, default_limit=10)
    print(paginated_price_history)
    return render(request, 'books/admin/Stock/admin_price_history.html', {
        'paginated_price_history': paginated_price_history,
        'limit': limit,
        'book': book,
        'headers': ['Old Price', 'New Price', 'Old Discount', 'New Discount', 'Changed By', 'Reason', 'Date']
    })


@login_required
def stockReservationView(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    reservation = book.stock.reservations.all().order_by('-created_at')
    paginated_stock_reservation, limit = paginate_queryset(request, reservation, default_limit=10)
    return render(request, 'books/admin/Stock/admin_stock_reservation.html', {
        'paginated_stock_reservation': paginated_stock_reservation,
        'limit': limit,
        'book': book,
        'headers': ['Order Item', 'Batch', 'Reserved Qty', 'Status', 'Created_At']
    })


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
