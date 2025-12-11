from math import floor, ceil

from django.db.models import Q, Max, Min
from django.http import HttpResponse
from openpyxl import Workbook

from Project_B.utils import applying_sorting, ALLOWED_SORTS
from src.books.models import Book
from src.stock.models import Stock


def search_query(query, manager=Book.objects):
    return manager.filter(
        Q(title__icontains=query) | Q(authors__name__icontains=query) | Q(
            publisher__name__icontains=query)).select_related('publisher', 'stock').prefetch_related('authors',
                                                                                                     'genres').distinct()


def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def searchfilter_bookStore(books, query=None, min_price=None, max_price=None, sort_by=None):
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(publisher__name__icontains=query)
        ).select_related('publisher', 'stock').prefetch_related('authors', 'genres').distinct()

    price_aggregate = Stock.objects.filter(is_available=True).aggregate(
        min_price=Min('current_price'),
        max_price=Max('current_price')
    )

    db_min_price = price_aggregate['min_price'] or 0
    db_max_price = price_aggregate['max_price'] or 10000

    db_min = floor(db_min_price)
    db_max = ceil(db_max_price / 100) * 100

    min_val, max_val = 0, db_max

    if min_price or max_price:

        min_val = to_int(min_price, 0)
        max_val = to_int(max_price, db_max)

        if min_val is None or min_val < 0:
            min_val = 0

        if max_val is None or max_val < 0 or max_val > db_max_price:
            max_val = db_max_price

        if min_val > max_val:
            min_val, max_val = 0, db_min_price

        if max_val > min_val and (max_val - min_val) < 500:
            max_val = min_val + 500

        min_val = floor(min_val)
        max_val = ceil(max_val / 100) * 100

        books = books.filter(stock__current_price__gte=min_val, stock__current_price__lte=max_val)

    books = applying_sorting(books, sort_by=sort_by, allowed_sorts=ALLOWED_SORTS["bookstore"],
                             default='-stock__is_available')

    return books, min_val, max_val, db_max


def export_excel(queryset):
    wb = Workbook()
    ws = wb.active
    ws.title = "Stocks"

    ws.append([
        "Book Title",
        "Authors",
        "Publisher",
        "Total Quantity",
        "Cost of Goods",
    ])

    for stock in queryset:
        ws.append([
            stock.book.title,
            ", ".join(a.name for a in stock.book.authors.all()),
            stock.book.publisher.name if stock.book.publisher else "",
            stock.total_quantity,
            float(stock.costofgoods),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="stocks.xlsx"'
    wb.save(response)
    return response
