from math import floor, ceil

from django.db.models import Q, Max, Min

from Project_B.utils import applying_sorting, ALLOWED_SORTS
from src.books.models import Book, Stock


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
        # books = search_query(query)
        books = books.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(publisher__name__icontains=query)
        ).select_related('publisher', 'stock').prefetch_related('authors', 'genres').distinct()

    price_aggregate = Stock.objects.filter(is_available=True).aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    db_min = floor(price_aggregate['min_price']) if price_aggregate['min_price'] else 0
    db_max = ceil(price_aggregate['max_price'] / 100) * 100 if price_aggregate['max_price'] else 10000

    # Initialize variables
    min_val, max_val = 0, db_max

    if min_price or max_price:
        # print("Min and max value", min_price, max_price)
        min_val = to_int(min_price, 0)
        max_val = to_int(max_price, db_max)

        # print("Min and max value after function: ", min_val, max_val)
        #
        # print('llll')
        # clamp values to real DB range
        if min_val is None or min_val < 0:
            min_val = 0
        if max_val is None or max_val < 0 or max_val > price_aggregate['max_price']:
            # print('h')
            max_val = price_aggregate['max_price']
            print(max_val)

        if min_val > max_val:
            min_val, max_val = 0, price_aggregate['min_price']

        if max_val > min_val and (max_val - min_val) < 500:
            max_val = min_val + 500

            # print('created gap between min and max val', min_val, max_val)

        # min_price_value = floor(price_aggregate['min_price']) if price_aggregate['min_price'] else 0
        # max_price_value = ceil(price_aggregate['max_price'] / 100) * 100 if price_aggregate['max_price'] else 10000

        min_val = floor(min_val)
        max_val = ceil(max_val / 100) * 100

        books = books.filter(stock__price__gte=min_val, stock__price__lte=max_val)
        # print('nnnnnn')

    # if sort_by:
    # print('sort_by')
    # print('mathi: ', sort_by)
    books = applying_sorting(books, sort_by=sort_by, allowed_sorts=ALLOWED_SORTS["bookstore"],
                             default='-stock__is_available')
    # print('book from sort: ', books)

    return books, min_val, max_val, db_max
