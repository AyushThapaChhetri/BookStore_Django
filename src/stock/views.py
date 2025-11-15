from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
# src/books/views.py (add/update these)
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from .forms import RestockForm, PriceUpdateForm  # From Step 3
from .models import Book, StockBatch
from .models import StockReservation
from .services import StockService
from .utils import validate_date_range
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
    history = stock.stock_history.order_by('created_at')[:10]
    price_history = stock.price_history.order_by('created_at')[:5]
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


# class StockBatchListView(View):
#     def get(self, request, book_uuid):
#         book = get_object_or_404(Book.objects.select_related('stock').prefetch_related('stock__batches'),
#                                  uuid=book_uuid)
#         batches = book.stock.batches.all().order_by('received_date', 'created_at')
#         paginated_batches, limit = paginate_queryset(request, batches, default_limit=10)
#         stock_batch_uuid = book.stock.batches.filter(uuid=book_uuid)
#
#         return render(request, 'books/admin/Stock/admin_stock_batches.html', {
#             'paginated_batches': paginated_batches,
#             'limit': limit,
#             'book': book,
#             'headers': ['Date', 'Initial', 'Remaining', 'Cost', 'Supplier', 'Notes', 'Actions']
#         })


class StockBatchListView(View):
    def get(self, request, book_uuid):
        book = get_object_or_404(
            Book.objects.select_related('stock').prefetch_related('stock__batches'),
            uuid=book_uuid
        )

        received_from = request.GET.get("received_from")
        received_to = request.GET.get("received_to")

        if received_from or received_to:
            try:
                from_date, to_date = validate_date_range(received_from, received_to)
            except ValidationError as e:
                print("ValidationError caught:", e)
                error_dict = e.message_dict
                print(error_dict)
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"errors": error_dict}, status=400)
                return render(request, "books/admin/Stock/admin_stock_batches.html", {
                    "paginated_batches": [],
                    "limit": 10,
                    "book": book,
                    "headers": ["Date", "Initial", "Remaining", "Cost", "Supplier", "Notes", "Actions"],
                    "errors": error_dict
                })
        else:
            from_date = to_date = None

        batches = book.stock.batches.all()
        if from_date and to_date:
            batches = batches.filter(received_date__gte=from_date, received_date__lte=to_date)

        batches = batches.order_by("received_date", "created_at")

        paginated_batches, limit = paginate_queryset(request, batches, default_limit=10)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            table_html = render_to_string(
                "books/admin/Stock/table/Stock_Batch_table_rows.html",
                {"paginated_batches": paginated_batches},
                request=request
            )
            pagination_html = render_to_string(
                "books/admin/Stock/pagination/stock_pagination.html",
                {"paginated_items": paginated_batches, "limit": limit},
                request=request
            )

            return JsonResponse({
                "table_html": table_html,
                "pagination_html": pagination_html
            })

        return render(request, "books/admin/Stock/admin_stock_batches.html", {
            "paginated_batches": paginated_batches,
            "limit": limit,
            "book": book,
            "headers": ["Date", "Initial", "Remaining", "Cost", "Supplier", "Notes", "Actions"]
        })


class StockBatchView(View):
    def get(self, request, book_uuid, batch_uuid=None):
        book = get_object_or_404(Book, uuid=book_uuid)
        stock = book.stock

        if not request.user.is_staff:
            return redirect('book_detail_store', book_uuid)

        if batch_uuid:

            is_ajax = True
            instance = get_object_or_404(StockBatch, uuid=batch_uuid, stock=stock)
            form = RestockForm(instance=instance)
        else:
            print("outside batch uid")
            is_ajax = False
            form = RestockForm(initial={'received_date': timezone.now().date()})

        context = {
            'form': form,
            'book': book,
            'is_ajax': is_ajax,
            'batch_uuid': batch_uuid,
        }

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string('books/components/admin_restock_form.html',
                                    context,
                                    request=request)
            return JsonResponse({'html': html})
        print("not html")
        # form = RestockForm(initial={'received_date': timezone.now().date()})
        return render(request, 'books/admin/Stock/admin_restock.html', context)

    def post(self, request, book_uuid, batch_uuid=None):
        if not request.user.is_authenticated:
            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({'error': 'Unauthorized'}, status=401)
            return PermissionDenied

        book = get_object_or_404(Book.objects.select_related('stock').prefetch_related('stock__batches'),
                                 uuid=book_uuid)
        stock = book.stock

        if not request.user.is_staff:
            return redirect('book_detail_store', book_uuid)

        if batch_uuid:
            print("from batch_uuid")
            batch = get_object_or_404(StockBatch, uuid=batch_uuid, stock=stock)
            form = RestockForm(request.POST, instance=batch)
        else:
            print("not from batch uid")
            form = RestockForm(request.POST)

        if form.is_valid():
            if batch_uuid:
                print("Before service")
                result = StockService.edit_stockBatch(form, book, request, batch_uuid)
                if not result.get("updated"):
                    if result.get("error"):
                        print("error , error")
                        messages.error(request, result["error"])
                    else:
                        print("error,info")
                        messages.error(request, result["message"])
                else:
                    # print("error,message")

                    messages.success(request, result["message"])

                if request.headers.get("X-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"message": result["message"], "updated": result["updated"]})

                return redirect('admin_stock_batches', book_uuid=book_uuid)

            StockService.restock(
                stock=stock,
                initial_quantity=form.cleaned_data['initial_quantity'],
                unit_cost=form.cleaned_data['unit_cost'],
                received_date=form.cleaned_data['received_date'],
                notes=form.cleaned_data['notes'],
                user=request.user
            )
            messages.success(request, "New batch added successfully.")
            return redirect('stock_detail', book_uuid)

        return render(request, 'books/admin/Stock/admin_restock.html', {'form': form, 'book': book})


@login_required
def stockHistoryView(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    stock_history = book.stock.stock_history.all().order_by('created_at')
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
    stock_price_history = book.stock.price_history.all().order_by('created_at')
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
def update_price(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    stock = book.stock

    if not request.user.is_staff:
        return redirect('book_detail_store', book_uuid)

    if request.method == 'POST':
        form = PriceUpdateForm(request.POST)
        if form.is_valid():
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
