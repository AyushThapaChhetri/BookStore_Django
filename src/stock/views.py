from datetime import datetime, time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db.models import DecimalField, Value, Min, Max, Q
from django.db.models import Prefetch
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from .forms import RestockForm, PriceUpdateForm
from .models import Book, StockHistory, PriceHistory
from .models import StockBatch
from .models import StockReservation
from .services import StockService, _calculate_opening_closing_stock
from .utils import validate_date_range
from ..books.pagination import paginate_queryset


@login_required
def stock_detail(request, book_uuid):
    book = get_object_or_404(
        Book.objects.select_related('stock').prefetch_related(
            Prefetch(
                'stock__batches',
                queryset=StockBatch.objects.select_related('supplier').order_by('received_date', 'created_at')[:10],
                to_attr='recent_batches'
            ),
            Prefetch(
                'stock__stock_history',
                queryset=StockHistory.objects.select_related('changed_by', 'batch').order_by('created_at')[:10],
                to_attr='recent_history'
            ),
            Prefetch(
                'stock__price_history',
                queryset=PriceHistory.objects.select_related('changed_by').order_by('created_at')[:5],
                to_attr='recent_price_history'
            ),
        ),
        uuid=book_uuid
    )
    stock = book.stock

    if not request.user.is_staff:
        return redirect('book_detail_store', book_uuid)

    reservations = StockReservation.objects.filter(
        batch__stock=stock,
        is_active=True
    ).select_related(
        'order_item',
        'order_item__order',
        'order_item__order__user',
        'order_item__book',
        'batch',
        'batch__stock',
        'batch__stock__book'
    ).order_by('-created_at')[:10]

    stock._cached_total_quantity = StockBatch.objects.filter(stock=stock).aggregate(
        total=Sum('remaining_quantity')
    )['total'] or 0

    context = {
        'book': book,
        'stock': stock,
        'batches': stock.recent_batches,
        'history': stock.recent_history,
        'price_history': stock.recent_price_history,
        'reservations': reservations,
    }

    return render(request, 'books/admin/Stock/admin_stock_detail_view.html', context)


class StockBatchListView(View):
    def get(self, request, book_uuid):
        book = get_object_or_404(
            Book.objects.select_related('stock'),
            uuid=book_uuid
        )

        received_from = request.GET.get("received_from")
        received_to = request.GET.get("received_to")
        batch_uuid = request.GET.get("batch_uuid")
        sort_by = request.GET.get("sort_by")

        sort_options = [
            ('profit', 'Profit'),
            ('loss', 'Loss'),
        ]

        date_range = book.stock.batches.aggregate(
            min_date=Min('received_date'),
            max_date=Max('received_date')
        )
        db_start = date_range['min_date']
        db_end = date_range['max_date']

        has_date_filter = False
        total_stock_quantity_all_time = StockBatch.objects.filter(stock_id=book.stock.id).aggregate(
            total_stock_quantity_all_time=Sum('initial_quantity')
        )['total_stock_quantity_all_time'] or 0

        print('Stock_quantity_all_time', total_stock_quantity_all_time)

        if received_from or received_to:
            try:
                from_date, to_date = validate_date_range(received_from, received_to)
                has_date_filter = True
            except ValidationError as e:
                error_dict = e.message_dict

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"errors": error_dict}, status=400)

                return render(request, "books/admin/Stock/admin_stock_batches.html", {
                    "paginated_batches": [],
                    "limit": 10,
                    "book": book,
                    "headers": [
                        "Uuid", "Date", "Initial", "Remaining", "Unit Cost",
                        "Stock In", "Stock Out", "Sold At", "Profit/Loss",
                        "Supplier", "Notes", "Actions"
                    ],
                    "sort_options": sort_options,
                    "errors": error_dict,
                    "from_value": received_from if received_from else "",
                    "to_value": received_to if received_to else "",
                    "min_date": db_start.isoformat() if db_start else "",
                    "max_date": db_end.isoformat() if db_end else "",
                })
        else:

            from_date = db_start
            to_date = db_end
            has_date_filter = False

        period_start = timezone.make_aware(datetime.combine(from_date, time.min)) if from_date else None
        period_end = timezone.make_aware(datetime.combine(to_date, time.max)) if to_date else None

        batches_qs = book.stock.batches.with_full_details(book.id)

        if batch_uuid:
            batches_qs = batches_qs.filter(uuid__icontains=batch_uuid)

        if has_date_filter:
            batches_qs = batches_qs.filter(received_date__range=[from_date, to_date])

        if sort_by == "profit":
            batches_qs = batches_qs.filter(net_amount__gt=0).order_by('-net_amount')
        elif sort_by == "loss":
            batches_qs = batches_qs.filter(net_amount__lt=0).order_by('net_amount')
        else:
            batches_qs = batches_qs.order_by("received_date", "created_at")

        opening_closing_data = _calculate_opening_closing_stock(
            book.stock,
            period_start,
            period_end,
            has_date_filter
        )

        # batch_no_a = 0
        # for batch in batches_qs:
        #     batch_no_a += 1

        totals = batches_qs.aggregate(
            total_sold=Coalesce(Sum('sold_amount'),
                                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))),
            total_cost=Coalesce(Sum('cost_amount'),
                                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)))
        )

        total_actual_sold_cost = totals['total_sold']
        total_actual_cost_cost = totals['total_cost']

        paginated_batches, limit = paginate_queryset(
            request,
            batches_qs,
            default_limit=10
        )
        # print("Batch above:", batch_no_a)

        for batch in paginated_batches:
            batch.actual_sold_cost = batch.sold_amount
            batch.actual_cost_amount = batch.cost_amount
            batch.actual_net_amount = batch.net_amount

        # print("Batch no:", batch_no)
        context = {
            "paginated_batches": paginated_batches,
            "total_actual_sold_cost": total_actual_sold_cost,
            "total_actual_cost_cost": total_actual_cost_cost,
            "total_stock_quantity_all_time": total_stock_quantity_all_time,
            "total_profit_loss": total_actual_sold_cost - total_actual_cost_cost,
            "limit": limit,
            "book": book,
            "headers": [
                "Uuid", "Date", "Initial", "Remaining", "Unit Cost",
                "Stock In", "Stock Out", "Sold At", "Profit/Loss",
                "Supplier", "Notes", "Actions"
            ],
            "sort_options": sort_options,
            "from_date": from_date,
            "to_date": to_date,
            "from_value": from_date.isoformat() if from_date else "",
            "to_value": to_date.isoformat() if to_date else "",
            "has_date_filter": has_date_filter,
            **opening_closing_data
        }

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
                # "opening_closing_html": opening_closing_html,
                "table_html": table_html,
                "pagination_html": pagination_html
            })

        return render(request, "books/admin/Stock/admin_stock_batches.html", context)


class StockBatchSoldDetailView(View):
    def get(self, request, batch_uuid):

        batch = get_object_or_404(
            StockBatch.objects.select_related('stock__book', 'supplier'),
            uuid=batch_uuid
        )

        book_id = batch.stock.book.id

        sold_order_ids = list(
            StockHistory.objects.filter(
                batch_id=batch.id,
                change_type='sold',
                stock__book_id=book_id,
                order__isnull=False
            ).values_list('order_id', flat=True).distinct()
        )

        if not sold_order_ids:
            context = {
                "batch": batch,
                "sold_details": [],
                "total_amount": Decimal("0.00"),
                "total_discount": Decimal("0.00"),
                "Grand_Total": Decimal("0.00"),
                "Profit_Loss": Decimal("0.00"),
                "Store_Cost": Decimal("0.00"),
            }
            return render(request, "books/admin/Stock/admin_sold_details.html", context)

        sold_reservations = StockReservation.objects.filter(
            batch_id=batch.id,
            order_item__book_id=book_id,
            order_item__order_id__in=sold_order_ids,
            is_active=False
        ).select_related(
            'order_item',
            'order_item__book',
            'order_item__order'
        ).order_by('order_item__order__created_at')

        sold_details = []
        total_discount = Decimal("0.00")
        total_amount = Decimal("0.00")
        sold_amount = Decimal("0.00")
        actual_sold_quantity = 0

        for reservation in sold_reservations:
            item = reservation.order_item
            quantity = reservation.reserved_quantity

            unit_price = Decimal(str(item.unit_price))
            discount_amount = Decimal(str(item.discount_amount or 0))
            unit_price_after_discount = unit_price - discount_amount
            line_total = unit_price_after_discount * quantity

            sold_details.append({
                "order_uuid": item.order.uuid,
                "book_title": item.book.title,
                "quantity": quantity,
                "unit_price": unit_price,
                "discount": discount_amount,
                "unit_price_after_discount": unit_price_after_discount,
                "line_total": line_total,
            })

            actual_sold_quantity += quantity
            total_discount += discount_amount * quantity
            total_amount += unit_price * quantity
            sold_amount += line_total

        store_cost = batch.unit_cost * actual_sold_quantity
        profit_loss = sold_amount - store_cost

        print("sold quantity", actual_sold_quantity)

        paginated_sold_details, limit = paginate_queryset(
            request,
            sold_details,
            default_limit=10
        )

        context = {
            "batch": batch,
            "sold_details": paginated_sold_details,
            "total_amount": total_amount,
            "total_discount": total_discount,
            "Grand_Total": sold_amount,
            "Profit_Loss": profit_loss,
            "Store_Cost": store_cost,
        }

        return render(request, "books/admin/Stock/admin_sold_details.html", context)


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


class StockHistoryView(View):
    def get(self, request, book_uuid=None):
        book = get_object_or_404(Book, uuid=book_uuid)
        stock_history = book.stock.stock_history.select_related(
            "batch", "changed_by"
        ).all()

        errors = {}

        changed_by = request.GET.get("changed_by")
        if changed_by:
            stock_history = stock_history.filter(changed_by__email__icontains=changed_by)

        change_type = request.GET.get("change_type")
        if change_type:
            valid_types = [key for key, _ in StockHistory.CHANGE_TYPES]
            if change_type not in valid_types:
                errors['change_type'] = "Invalid change type selected."
            else:
                stock_history = stock_history.filter(change_type=change_type)

        start = request.GET.get("received_from")
        end = request.GET.get("received_to")

        date_range = book.stock.stock_history.aggregate(
            min_date=Min('created_at'),
            max_date=Max('created_at')
        )

        db_start = date_range['min_date'].date() if date_range['min_date'] else None
        db_end = date_range['max_date'].date() if date_range['max_date'] else None

        has_date_filter = False
        start_date = None
        end_date = None

        default_open_close = {
            'opening_quantity': 0,
            'opening_value': Decimal('0.00'),
            'closing_quantity': 0,
            'closing_value': Decimal('0.00'),
            'order_process': 0,
            'stock_not_placed': 0,

            'sold_quantity': 0,
            'restock_today': 0,
            'restock_with_adjustment': 0,
            'adjustment_today': 0,
            'reserve_today': 0,
            'release_today': 0,
        }

        if start or end:
            try:
                start_date, end_date = validate_date_range(start, end)
                if start_date:
                    stock_history = stock_history.filter(created_at__date__gte=start_date)
                if end_date:
                    stock_history = stock_history.filter(created_at__date__lte=end_date)

                has_date_filter = True
            except ValidationError as e:
                errors.update(e.message_dict)
                error_dict = e.message_dict

                print("Error before")

                if request.GET.get("ajax"):
                    print("Error in")
                    return JsonResponse({"errors": error_dict}, status=400)
                print("Error after")

                return render(request, "books/admin/Stock/admin_stock_history.html", {
                    "paginated_batches": [],
                    'limit': 10,
                    'book': book,
                    'headers': ['Type', 'Change', 'Before', 'After', 'Batch Uuid', 'By', 'Date'],
                    "min_date": db_start.isoformat() if db_start else "",
                    "max_date": db_end.isoformat() if db_end else "",
                    "from_value": start,
                    "to_value": end,
                    "errors": error_dict,
                    **default_open_close
                })
        else:

            start_date = db_start
            end_date = db_end
            has_date_filter = False

        from_value = start_date.isoformat() if start_date else ""
        to_value = end_date.isoformat() if end_date else ""

        period_start = timezone.make_aware(datetime.combine(start_date, time.min)) if start_date else None
        period_end = timezone.make_aware(datetime.combine(end_date, time.max)) if end_date else None

        opening_closing_data = {}
        if period_start and period_end:
            opening_closing_data = _calculate_opening_closing_stock(
                book.stock,
                period_start,
                period_end,
                has_date_filter
            )

        print("From history: ", opening_closing_data)

        batches_qs = book.stock.batches.with_full_details(book.id)

        if has_date_filter:
            batches_qs = batches_qs.filter(received_date__range=[start_date, end_date])

        # store cost for the item and sales revenue
        totals = batches_qs.aggregate(
            total_sold=Coalesce(Sum('sold_amount'),
                                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))),
            total_cost=Coalesce(Sum('cost_amount'),
                                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))),

        )

        total_stock_quantity_all_time = StockBatch.objects.filter(stock_id=book.stock.id).aggregate(
            total_stock_quantity_all_time=Sum('initial_quantity')
        )['total_stock_quantity_all_time'] or 0

        print('Stock_quantity_all_time', total_stock_quantity_all_time)

        if end_date:
            date_total_stock_till_time_select = timezone.make_aware(datetime.combine(end_date, time.max))
        else:
            today = timezone.localdate()
            date_total_stock_till_time_select = timezone.make_aware(datetime.combine(today, time.max))

        stock_history_div = (StockHistory.objects.
        filter(stock_id=book.stock.id,
               created_at__lte=date_total_stock_till_time_select)
        .aggregate(
            total_restock_div=Coalesce(Sum('quantity_change', filter=Q(
                change_type='restock'
            )), 0),
            total_edit_div=Coalesce(Sum('quantity_change', filter=Q(
                change_type='editstock'
            )), 0),

        )
        )

        total_stock_in_till_date = stock_history_div['total_restock_div'] + stock_history_div['total_edit_div']

        total_actual_sold_cost = totals['total_sold']
        total_actual_cost_cost = totals['total_cost']
        # total_actual_stock_all_time = totals['total_stock_all_time']

        opening_closing_data = {
            "total_actual_stock_all_time": total_stock_in_till_date,
            "total_actual_sold_cost": total_actual_sold_cost,
            "total_actual_cost_cost": total_actual_cost_cost, **default_open_close,
            **opening_closing_data}

        if request.GET.get("ajax") and errors:
            return JsonResponse({"errors": errors, "table_html": "", "pagination_html": ""}, status=400)

        stock_history = stock_history.order_by('created_at')
        paginated_stock_history, limit = paginate_queryset(request, stock_history, default_limit=10)

        if request.GET.get("ajax"):
            opening_closing_html = render_to_string(
                "books/components/stock/stock_batch_openingClosing.html",
                opening_closing_data,
                request=request
            )

            table_html = render_to_string(
                "books/admin/Stock/table/stock_history_table.html",
                {"paginated_stock_history": paginated_stock_history}
            )
            pagination_html = render_to_string(
                "books/admin/Stock/pagination/stock_pagination.html",
                {"paginated_items": paginated_stock_history, "limit": limit}
            )
            return JsonResponse({"opening_closing_html": opening_closing_html, "table_html": table_html,
                                 "pagination_html": pagination_html})

        return render(request, 'books/admin/Stock/admin_stock_history.html', {
            'paginated_stock_history': paginated_stock_history,
            'limit': limit,
            'book': book,
            'headers': ['Type', 'Change', 'Before', 'After', 'Batch Uuid', 'By', 'Date'],
            'change_type_options': StockHistory.CHANGE_TYPES,
            'errors': errors,
            "min_date": db_start.isoformat() if db_start else "",
            "max_date": db_end.isoformat() if db_end else "",
            "total_actual_sold_cost": total_actual_sold_cost,
            "total_actual_cost_cost": total_actual_cost_cost,
            "from_value": from_value,
            "to_value": to_value,
            **opening_closing_data

        })


@login_required
def stockPriceView(request, book_uuid):
    book = get_object_or_404(Book, uuid=book_uuid)
    stock_price_history = book.stock.price_history.select_related('changed_by').all().order_by('created_at')
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

    reservation = book.stock.reservations.select_related(
        'batch',
        'batch__stock',
        'batch__stock__book',
        'order_item',
        'order_item__book',
        'order_item__order',
        'order_item__order__user',
    ).all().order_by('-created_at')
    print("hello")
    paginated_stock_reservation, limit = paginate_queryset(request, reservation, default_limit=10)
    return render(request, 'books/admin/Stock/admin_stock_reservation.html', {
        'paginated_stock_reservation': paginated_stock_reservation,
        'limit': limit,
        'book': book,
        'headers': ['Order Item', 'Batch', 'Reserved Qty', 'Reserved By', 'Status', 'Created_At']
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
