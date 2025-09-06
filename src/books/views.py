import json
from decimal import Decimal
from math import ceil, floor
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Min, Max, F
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from pygments.lexers import q

from Project_B.utils import applying_sorting, ALLOWED_SORTS
from src.books.forms import BookForm, AuthorForm, GenreForm, PublisherForm, StockForm
from src.books.models import Book, Stock, Author, Publisher, Genre
from src.books.pagination import paginate_queryset
from src.cart.models import CartItem, Cart
from src.cart.utils import calculate_cart_totals, round_decimal
from src.orders.models import Order, OrderItem
from src.shipping.forms import DeliveryForm
from src.shipping.models import DeliveryInfo


# Create your views here.
def hello(request):
    # return render(request, '../../Project_B/templates/books/hello.html', {'name': 'Ayush'})
    return render(request, 'books/hello.html', {'name': 'Ayush'})
    # return render(request, 'hello.html')
    # return HttpResponse("Hello, %s!" % request.path)


# def search_query(query):
#     return (Book.objects.filter(Q(title__icontains=query) | Q(authors__name__icontains=query) | Q(
#         publisher__name__icontains=query)).select_related('publisher', 'stock').prefetch_related('authors',
#                                                                                                  'genres').distinct())

def search_query(query, manager=Book.objects):
    return manager.filter(
        Q(title__icontains=query) | Q(authors__name__icontains=query) | Q(
            publisher__name__icontains=query)).select_related('publisher', 'stock').prefetch_related('authors',
                                                                                                     'genres').distinct()


def search_books(request):
    query = request.GET.get('q', '').strip()
    # makes true or false if deleted is send with 1 value
    deleted = request.GET.get('deleted', '0') == '1'

    manager = Book.deleted_objects if deleted else Book.objects

    print("Query from search: ", query)
    print("Deleted from search: ", deleted)

    # books = search_query(query)
    books = search_query(query, manager)

    data = []
    for book in books:
        stock_info = None
        if hasattr(book, 'stock') and book.stock:
            stock_info = {
                'uuid': str(book.stock.uuid),
                'price': float(book.stock.price),
                "stock_quantity": book.stock.stock_quantity,
                "is_available": book.stock.is_available,
                "discount_percentage": float(book.stock.discount_percentage),
                "discount_amount": float(book.stock.discount_amount),
                "last_restock_date": book.stock.last_restock_date,
            }
        data.append({
            'uuid': book.uuid,
            'title': book.title,
            'authors': [author.name for author in book.authors.all()],
            'publisher': book.publisher.name if book.publisher else None,
            'genres': [genre.name for genre in book.genres.all()],
            'description': book.description,
            "pages": book.pages,
            "language": book.language,
            "isbn": book.isbn,
            "publication_date": book.publication_date,
            "edition": book.edition,
            "cover_image": book.cover_image.url if book.cover_image else None,
            "stock": stock_info,
            'created_at': book.created_at if book.created_at else None,
            'updated_at': book.updated_at if book.updated_at else None,
            'deleted_by': book.deleted_by.email if book.deleted_by else None,
            'deleted_at': book.deleted_at if book.deleted_at else None,
        })

    return JsonResponse({'books': data})


def search_authors(request):
    query = request.GET.get('q', '').strip()
    # print("search authors hit", query)
    authors = Author.objects.filter(
        Q(name__icontains=query) |
        Q(nationality__icontains=query) |
        Q(bio__icontains=query)
    ).distinct()

    # print('Authors', authors)
    data = []
    for author in authors:
        data.append({
            'uuid': str(author.uuid),
            'name': author.name,
            'bio': author.bio,
            'birth_date': author.birth_date,
            'death_date': author.death_date,
            'nationality': author.nationality,
            'website': author.website,
            'profile_image': author.profile_image.url if author.profile_image else None,
            'created_at': author.created_at,
            'updated_at': author.updated_at,
        })
    # print('Authors all data', data)
    return JsonResponse({'authors': data})


def search_publishers(request):
    query = request.GET.get('q', '').strip()

    publishers = Publisher.objects.filter(
        Q(name__icontains=query) |
        Q(address__icontains=query) |
        Q(contact_email__icontains=query)
    ).distinct()

    data = []
    for publisher in publishers:
        data.append({
            'uuid': str(publisher.uuid),
            'name': publisher.name,
            'founded_year': publisher.founded_year,
            'website': publisher.website,
            'address': publisher.address,
            'contact_email': publisher.contact_email,
            'description': publisher.description,
            'created_at': publisher.created_at,
            'updated_at': publisher.updated_at,
        })

    return JsonResponse({'publishers': data})


def search_genres(request):
    query = request.GET.get('q', '').strip()

    genres = Genre.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(parent_genre__name__icontains=query)
    ).select_related('parent_genre').distinct()

    data = []
    for genre in genres:
        data.append({
            'uuid': str(genre.uuid),
            'name': genre.name,
            'description': genre.description,
            'parent_genre': genre.parent_genre.name if genre.parent_genre else None,
            'created_at': genre.created_at,
            'updated_at': genre.updated_at,
        })

    return JsonResponse({'genres': data})


@require_POST
@login_required
def add_to_cart(request):
    book_uuid = request.POST.get('book_uuid')
    if not book_uuid:
        return JsonResponse({'success': False, 'message': 'No book uuid provided'}, status=400)

    book = get_object_or_404(Book, uuid=book_uuid)

    if book.stock.stock_quantity <= 0:
        return JsonResponse({'success': False, 'message': f"'{book.title}' is sold out"}, status=400)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    # print('Cart: ',cart)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    # print('Cart Item: ',cart_item)
    cart_item.unit_price = book.stock.price
    # total discount for that item only
    cart_item.discount_amount = book.stock.discount_amount

    if created:
        # First Time
        message = f"{book.title} added to cart"
    else:
        # Already in cart
        message = f"{book.title} is already on cart"

    cart_item.save()

    return JsonResponse({
        'success': True,
        'created': created,
        'message': f"{book.title} added to cart",
        'quantity': cart_item.quantity,
        'total_price': cart.get_total_price,
        'cart_items_count': cart.items.count(),
        'cart_item_uuid': str(cart_item.uuid),
    })


@require_POST
@login_required
def update_cart(request, item_uuid):
    print('cart item uuid form update: ', item_uuid)

    # Check if missing or invalid UUID
    try:
        item_uuid = UUID(item_uuid)
    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "error": "Invalid or missing item uuid"},
            status=400
        )

    data = json.loads(request.body)
    quantity = int(data.get('quantity', 1))
    action = str(data.get('action', ''))
    print("Item Uuid: ", item_uuid)

    try:
        item = CartItem.objects.get(uuid=item_uuid, cart__user=request.user)
        book = item.book
        message = None

        # Handle increment
        if action == 'increment':
            if item.quantity >= book.stock.stock_quantity:
                # Can't go above stock
                quantity = book.stock.stock_quantity
                message = f"Only {book.stock.stock_quantity} left in stock."
            else:
                quantity = item.quantity + 1

        # Handle decrement
        elif action == 'decrement':
            if item.quantity <= 1:
                quantity = 1
                message = "Quantity cannot be less than 1."
            else:
                quantity = item.quantity - 1

        # Handle other cases (like stock dropped between sessions)
        if quantity > book.stock.stock_quantity:
            quantity = max(book.stock.stock_quantity, 1)
            message = f"Stock updated. Only {book.stock.stock_quantity} left now."

        item.quantity = quantity
        item.save()

        # cart = Cart.objects.get_or_create(user=request.user)[0]
        # total_price = sum(i.get_subtotal() for i in cart.items.all())

        #  Use centralized cart totals
        totals = calculate_cart_totals(request.user)
        print(totals)
        response = {
            "success": True,
            "quantity": item.quantity,
            "subtotal": item.cart.get_total_price,
            "available_stock": book.stock.stock_quantity,
            "total_price": totals["total_price"],
            "total_discount": totals["total_discount"],
            "total_amount_after_discount": totals["total_amount_after_discount"],
            "total_quantity": totals["total_quantity"],
        }
        if message:
            response["message"] = message

        return JsonResponse(response)

    except CartItem.DoesNotExist:
        return JsonResponse({"success": False, "error": "Item not found."}, status=404)


@require_POST
@login_required
def remove_cart_item(request, item_uuid):
    print("outside")
    try:
        print("Inside 1")
        item = CartItem.objects.get(uuid=item_uuid, cart__user=request.user)
        item.delete()
        print("Inside 2")
        return JsonResponse({"success": True})

    except CartItem.DoesNotExist:
        return JsonResponse({"success": False, "error": "Item not found"}, status=404)


def clear_cart(request):
    cart = Cart.objects.get(user=request.user)
    cart.items.all().delete()
    return redirect('book_store')


class BookAdminView(View):
    def get(self, request):
        return render(request, 'base/admin/admin_base.html')


# List all books (Read)
class BookListView(View):
    # login_url = 'login_view'  # Optional: redirect URL for unauthenticated users

    # redirect_field_name = 'next'  # Optional: default is 'next'

    def get(self, request):
        # limit = request.GET.get('limit', 10)
        # try:
        #     limit = int(limit)
        # except (ValueError, TypeError):
        #     limit = 10  # fallback to default
        #
        # books = Book.objects.all().order_by('-created_at')
        #
        # # Set Up Pagination
        # p = Paginator(Book.objects.all().order_by('created_at'), limit)
        # page = request.GET.get('page')
        # paginated_books = p.get_page(page)

        # pagination int paginate.py
        # books = Book.objects.all().order_by('-created_at')
        books = (
            Book.objects.all()
            .select_related('publisher', 'stock')
            .prefetch_related('authors', 'genres')
        )
        # first_book = books.values().first()
        # for key, value in first_book.items():
        #     print(key, ' : ', value)
        # author = Author.objects.filter(books__in=books)

        books = applying_sorting(books, request, ALLOWED_SORTS["book"])

        paginated_books, limit = paginate_queryset(request, books, default_limit=10)

        return render(request, 'books/admin/admin_book_list.html', {'books': books,
                                                                    'paginated_books': paginated_books,
                                                                    'limit': limit,
                                                                    'add_perm': "book.add_book",
                                                                    "sort": request.GET.get("sort", "created_desc"),
                                                                    })


class BookRecycleBinListView(View):
    def get(self, request):
        # Get deleted books using your soft delete manager
        books = Book.deleted_objects.all().select_related('publisher', 'stock').prefetch_related('authors', 'genres')
        # print('Recycled', books)
        books = applying_sorting(books, request, ALLOWED_SORTS["book"])
        paginated_books, limit = paginate_queryset(request, books, default_limit=10)
        # print(books)
        # for book in books.values():

        context = {
            'books': books,
            'paginated_books': paginated_books,
            'limit': limit,
            'is_recycle_bin': True,  # Flag to indicate we're in recycle bin
        }
        return render(request, 'books/admin/admin_book_list.html', context)


class BookRestoreView(View):
    def post(self, request, uuid):
        if not request.user.has_perm('books.change_book'):
            raise PermissionDenied

        try:
            with transaction.atomic():
                book = get_object_or_404(Book.deleted_objects, uuid=uuid)
                book.restore()

                book.stock.restore()

        except Exception as e:
            print(e)

        messages.success(request, f"'{book.title}' has been restored successfully.")
        return redirect('book_recycle_bin')


class BookPermanentDeleteView(View):
    def post(self, request, uuid):
        if not request.user.has_perm('books.delete_book'):
            raise PermissionDenied

        book = get_object_or_404(Book.deleted_objects, uuid=uuid)
        book_title = book.title

        try:
            with transaction.atomic():
                # Hard delete related stock first
                if hasattr(book, 'stock') and book.stock:
                    book.stock.hard_delete()

                # Now hard delete the book itself
                book.hard_delete()

            messages.success(request, f"'{book_title}' has been permanently deleted.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect('book_recycle_bin')


# List all Stock (Read)
class StockListView(View):

    def get(self, request):
        stocks = (
            Stock.objects.all()
            .select_related('book')

        )

        # print("Stocks : ", stocks)

        stocks = applying_sorting(stocks, request, ALLOWED_SORTS["stock"])

        # print("After applying sorting Stocks : ", stocks)
        paginated_stocks, limit = paginate_queryset(request, stocks, default_limit=10)

        return render(request, 'books/admin/admin_stock_list.html', {'stocks': stocks,
                                                                     'paginated_stocks': paginated_stocks,

                                                                     'limit': limit})


# View specific books(Read)
class BookDetailView(View):
    def get(self, request, uuid):
        book = get_object_or_404(
            Book.objects.select_related("publisher", "stock").prefetch_related("authors", "genres"),
            uuid=uuid
        )
        return render(request, 'books/admin/book_detail_view.html', {'book': book})


# View specific stock(Read)
class StockDetailView(View):
    def get(self, request, uuid):
        stock = get_object_or_404(
            Stock.objects.select_related("book"),
            uuid=uuid
        )
        return render(request, 'books/admin/stock_detail_view.html', {'stock': stock})


@method_decorator(never_cache, name='dispatch')
class BookStore(View):
    def get(self, request):
        query = request.GET.get('q', '')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')

        # books = Book.objects.all()
        # start with Book queryset
        books = Book.objects.all().annotate(
            price=F('stock__price'),
            stock_quantity=F('stock__stock_quantity'),
            is_available=F('stock__is_available'),
            last_restock_date=F('stock__last_restock_date')
        )
        items_count = CartItem.objects.filter(cart__user=request.user).count()

        books = applying_sorting(books, request, ALLOWED_SORTS["bookstore"])

        if query:
            books = search_query(query)

        print('before books', books)
        if min_price and max_price:
            try:
                min_val = int(min_price)
                max_val = int(max_price)
                print("Min and max value", min_val, max_val)
                books = books.filter(stock__price__gte=min_val, stock__price__lte=max_val)
                print('after filter', books)
            except ValueError:
                pass

        # books = Book.objects.all().order_by('-created_at')
        paginated_books, limit = paginate_queryset(request, books, default_limit=12)

        # compute min/max prices of the available stock
        price_aggregate = Stock.objects.filter(is_available=True).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        min_price_value = floor(price_aggregate['min_price']) if price_aggregate['min_price'] else 0
        max_price_value = ceil(price_aggregate['max_price'] / 100) * 100 if price_aggregate['max_price'] else 10000

        print("min and max", min_price_value, max_price_value)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            print("hello from headers")
            cards_html = render_to_string("books/components/book_cards.html", {'paginated_books': paginated_books, })
            pagination_html = render_to_string('books/components/pagination_div.html',
                                               {'paginated_books': paginated_books})

            return JsonResponse({
                "cards": cards_html,
                "pagination": pagination_html,
                'items_count': items_count,
                "min_price": min_price_value,
                "max_price": max_price_value,
            })

            # return render(request, "books/components/book_cards.html", {
            #     "paginated_books": paginated_books,
            #     "limit": limit
            # })

        return render(request, 'books/book_store.html', {'books': books,
                                                         'paginated_books': paginated_books,
                                                         'limit': limit,
                                                         'min_price_value': min_price_value,
                                                         'max_price_value': max_price_value,
                                                         })

        # return render(request, 'books/book_store.html', context)


def is_cart_item_exists(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if not cart or not cart.items.exists():
        return redirect('book_cart')
    return None


class BookCheckout(View):
    def get(self, request):
        redirect_response = is_cart_item_exists(request)
        if redirect_response:
            return redirect_response

        delivery_instance = None

        # First session
        delivery_uuid = request.session.get('delivery_uuid')
        if delivery_uuid:
            delivery_instance = DeliveryInfo.objects.filter(
                uuid=delivery_uuid,
                user=request.user
            ).first()

        # If session is missing/invalid, fallback to latest delivery
        if not delivery_instance:
            delivery_instance = DeliveryInfo.objects.filter(user=request.user).order_by('-created_at').first()

        form = DeliveryForm(instance=delivery_instance)

        # --- Cart stock validation ---
        cart = Cart.objects.get_or_create(user=request.user)[0]
        items = cart.items.all()
        stock_adjusted = False

        for item in items:
            if item.quantity > item.book.stock.stock_quantity:
                item.quantity = max(item.book.stock.stock_quantity, 1)  # keep at least 1
                item.save()
                stock_adjusted = True
                messages.warning(
                    request,
                    f"{item.book.title} quantity adjusted to {item.quantity} due to stock limits."
                )

            # total_price = sum(item.get_subtotal() for item in items)
            # total_quantity = cart.items.aggregate(Sum('quantity'))[
            #                      'quantity__sum'
            #                  ] or 0
            # --- Use centralized cart totals ---

        # print("Form")
        # print(form)
        # return render(request, 'books/book_checkout.html',
        #               {'form': form, 'total_price': total_price, 'total_quantity': total_quantity})

        totals = calculate_cart_totals(request.user)
        return render(request, 'books/book_checkout.html',
                      {'form': form, **totals})

    def post(self, request):
        form = DeliveryForm(request.POST)
        if form.is_valid():
            delivery_instance = form.save(commit=False)
            delivery_instance.user = request.user
            delivery_instance.save()

            request.session['delivery_uuid'] = str(delivery_instance.uuid)
            return JsonResponse({'success': True, 'redirect_url': reverse('book_payment')})
        else:
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)


class BookCheckoutPayment(View):
    def get(self, request):
        redirect_response = is_cart_item_exists(request)
        if redirect_response:
            return redirect_response

        delivery_uuid = request.session.get('delivery_uuid')
        delivery_instance = None

        if delivery_uuid:
            try:
                delivery_instance = DeliveryInfo.objects.get(uuid=delivery_uuid, user=request.user)
            except DeliveryInfo.DoesNotExist:
                delivery_instance = None
        else:
            return redirect('book_cart')

        # cart = Cart.objects.get_or_create(user=request.user)[0]
        # items = cart.items.all()
        # total_quantity = cart.items.aggregate(Sum('quantity'))['quantity__sum'] or 0
        # total_price = sum(item.get_subtotal() for item in items)
        cart_totals = calculate_cart_totals(request.user)
        total_discount = cart_totals["total_discount"]
        total_quantity = cart_totals["total_quantity"]
        total_price = cart_totals['total_price']
        total_amount_after_discount = cart_totals['total_amount_after_discount']

        return render(request, 'books/book_payment.html', {'delivery': delivery_instance,
                                                           'total_price': total_price,
                                                           'total_discount': total_discount,
                                                           'total_amount_after_discount': total_amount_after_discount,
                                                           'total_quantity': total_quantity})

    def post(self, request):
        payment_method = request.POST.get('payment_method')
        if not payment_method:
            return redirect('book_payment')

        # Get card
        redirect_response = is_cart_item_exists(request)
        if redirect_response:
            return redirect_response

        # Get Delivery info
        delivery_uuid = request.session.get('delivery_uuid')
        delivery_instance = None
        if delivery_uuid:
            delivery_instance = DeliveryInfo.objects.filter(uuid=delivery_uuid, user=request.user).first()

        if not delivery_instance:
            delivery_instance = request.user.addresses.order_by('-created_at').first()

        # cart, _ = Cart.objects.get_or_create(user=request.user)
        # items = cart.items.all()
        # total_amount = sum(item.get_subtotal() for item in items)
        cart_totals = calculate_cart_totals(request.user)
        cart = cart_totals['cart']
        items = cart_totals["items"]
        # total_amount = cart_totals['total_amount_after_discount']
        total_amount = cart.total_after_discount_shipping
        shopping_cost = cart.shipping_cost
        try:
            with transaction.atomic():
                # locked_books = {}
                locked_objects = {}
                for item in items:
                    book = Book.objects.select_for_update().get(id=item.book.id)
                    stock = Stock.objects.select_for_update().get(book=book)
                    if item.quantity > stock.stock_quantity:
                        messages.error(request, f"Not enough stock for {book.title}")
                        return redirect('book_cart')
                    # locked_books[item.book.id] = book
                    locked_objects[item.book.id] = (book, stock)
                order = Order.objects.create(
                    user=request.user,
                    status='pending',
                    total_amount=total_amount,
                    shipping_address=delivery_instance,
                    shipping_cost=shopping_cost,
                )

                request.session['order_uuid'] = str(order.uuid)

                for item in items:
                    # book = Book.objects.select_for_update().get(id=item.book.id)
                    book, stock = locked_objects[item.book.id]
                    OrderItem.objects.create(
                        order=order,
                        book=item.book,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        discount_amount=item.discount_amount,
                    )

                    # Reduce stock
                    print("Stock Q Before", stock.stock_quantity)
                    stock.stock_quantity -= item.quantity
                    stock.save(update_fields=["stock_quantity"])
                    print("Stock Q After", stock.stock_quantity)

                # Clear cart only after success
                cart.items.all().delete()
                order_items = order.items.all()

                if delivery_uuid:
                    del request.session['delivery_uuid']

                messages.success(request, f"Order Successful")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('book_cart')

        return redirect('book_order_complete')


class BookOrderComplete(View):
    def get(self, request):
        order_uuid = request.session.get('order_uuid')
        if not order_uuid:
            return redirect('book_cart')

        order = Order.objects.get(uuid=order_uuid, user=request.user)
        if not order:
            return redirect('book_cart')

        del request.session['order_uuid']
        order_items = order.items.all()

        subtotal = sum((item.base_price for item in order_items), start=Decimal('0.00'))
        discount = sum((item.discount_amount * item.quantity for item in order_items), start=Decimal('0.00'))
        total_price = sum((item.total_price_after_discount for item in order_items),
                          start=Decimal('0.00')) + order.shipping_cost

        return render(request, 'books/order_complete.html', {
            'order': order,
            'order_items': order_items,
            'shipping_cost': order.shipping_cost,
            # 'subtotal': sum(item.base_price for item in order.items.all()),
            # 'discount': order.get_total_discount,
            # 'total_price': order.total_after_shipping_discount,
            'subtotal': round_decimal(subtotal),
            'discount': round_decimal(discount),
            'total_price': round_decimal(total_price),

        })


@method_decorator(never_cache, name='dispatch')
class BookCart(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')

        # cart = Cart.objects.get_or_create(user=request.user)[0]
        # items = cart.items.all()
        # items_count = cart.items.count()
        # total_quantity = cart.items.aggregate(Sum('quantity'))[
        #                      'quantity__sum'
        #                  ] or 0

        # total_price = sum(item.get_subtotal() for item in items)

        # items_discount_prices = []
        # for item in items:
        #     discount_price = item.stock.price * (item.stock.discount_percentage / 100) * item.quantity
        #     items_discount_prices.append(discount_price)
        # total_discount = sum(items_discount_prices)
        #
        # total_price_after_discount = total_price - total_discount

        # Use Decimal for precise calculations
        # total_price = sum(
        #     (Decimal(str(item.get_subtotal())) for item in items),
        #     start=Decimal('0.00')
        # )
        #
        # total_discount = sum(
        #     (
        #         Decimal(str(item.book.stock.price)) *
        #         Decimal(str(item.book.stock.discount_percentage)) / Decimal('100') *
        #         item.quantity
        #         for item in items
        #     ),
        #     start=Decimal('0.00')
        # )
        #
        # total_amount_after_discount = total_price - total_discount
        #
        # # Round to 2 decimal points
        # total_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # total_discount = total_discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # total_amount_after_discount = total_amount_after_discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        totals = calculate_cart_totals(request.user)

        return render(request, 'books/book_cart.html',
                      # {'cart': cart, 'items': items, 'items_count': items_count, 'total_quantity': total_quantity,
                      #  'total_price': total_price, 'total_discount': total_discount,
                      #  'total_amount_after_discount': total_amount_after_discount}
                      totals
                      )


@method_decorator(never_cache, name='dispatch')
class BookDetailStore(View):
    def get(self, request, uuid):
        book = get_object_or_404(Book, uuid=uuid)
        cart = Cart.objects.get_or_create(user=request.user)[0]

        # Try to get the CartItem for this book in the user's cart
        book_in_cart = CartItem.objects.filter(cart=cart, book=book).first()

        # Safely define quantity
        quantity = book_in_cart.quantity if book_in_cart else 1

        # Pass the CartItem UUID to template (or None if not in cart)
        cart_item_uuid = str(book_in_cart.uuid) if book_in_cart else None
        print('Cart uuid from detail store: ', cart_item_uuid)

        return render(request, 'books/book_detail_store.html',
                      {'books': book, 'book_in_cart': book_in_cart, 'quantity': quantity,
                       'cart_item_uuid': cart_item_uuid, })


class BookView(View):
    def get(self, request, uuid=None):
        form = BookForm()
        print("Uuid from bookview: ", uuid)
        # print(form)
        if uuid:
            print("Edit")
            book = get_object_or_404(Book, uuid=uuid)
            form = BookForm(instance=book)
            return render(request, 'books/admin/book_create_or_edit.html', {'form': form})
        print("Create")
        return render(request, 'books/admin/book_create_or_edit.html', {'form': form})

    def post(self, request, uuid=None):
        print("Create Post before")
        if uuid and 'delete' in request.POST:
            print("Delete")
            if not request.user.has_perm('books.delete_book'):
                raise PermissionDenied

            try:
                with transaction.atomic():
                    book = get_object_or_404(Book.all_objects, uuid=uuid)
                    print("book found", book)
                    # If previously restored
                    book.refresh_from_db()  # reload deleted_at and deleted_by from DB

                    if book.is_deleted:
                        print('aa')
                        messages.warning(request, "This book is already deleted.")
                    else:
                        print('bb')
                        try:
                            if hasattr(book, 'stock') and book.stock:
                                book.stock.delete(user=request.user)
                                # time

                            book.delete(user=request.user)
                            print("gg")
                            messages.success(request, "Book deleted successfully.")
                        except Exception as e:
                            print(e)

                    return redirect('admin-book-list')

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return redirect('admin-book-list')
        # Edit
        if uuid:
            print("Edit")
            if not request.user.has_perm('books.change_book'):
                raise PermissionDenied
            book = get_object_or_404(Book, uuid=uuid)
            form = BookForm(request.POST, request.FILES, instance=book)  # attach instance here
            if form.is_valid():
                form.save()
                return redirect('admin-book-list')
            return render(request, 'books/admin/book_create_or_edit.html', {'form': form})

        # Create
        print("Create Post After")
        print(request.FILES)
        if not request.user.has_perm('books.add_book'):
            raise PermissionDenied
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin-book-list')
        return render(request, 'books/admin/book_create_or_edit.html', {'form': form})


class StockView(View):
    def get(self, request, uuid=None):
        form = StockForm()
        # print(form)
        if uuid:
            print("Stock Edit")
            stock = get_object_or_404(Stock, uuid=uuid)
            form = StockForm(instance=stock)
            return render(request, 'books/admin/stock_create_or_edit.html', {'form': form})
        print("Create Stock")
        return render(request, 'books/admin/stock_create_or_edit.html', {'form': form})

    def post(self, request, uuid=None):
        print("Create Post before")
        if uuid and 'reset' in request.POST:
            print("Reset")
            if not request.user.has_perm('stock.delete_stock'):
                raise PermissionDenied
            stock = get_object_or_404(Stock, uuid=uuid)
            # Reset values instead of deleting
            stock.price = 0.00
            stock.stock_quantity = 0
            stock.is_available = False
            stock.discount_percentage = 0.00
            stock.last_restock_date = None
            stock.save()
            return redirect('admin-stock-list')

        # Edit
        if uuid:
            print("Edit Stock")
            if not request.user.has_perm('stock.change_stock'):
                raise PermissionDenied
            stock = get_object_or_404(Stock, uuid=uuid)
            form = StockForm(request.POST, request.FILES, instance=stock)  # attach instance here
            if form.is_valid():
                form.save()
                return redirect('admin-stock-list')
            return render(request, 'books/admin/stock_create_or_edit.html', {'form': form})

        # Create
        print("Create Post After Stock")
        print(request.FILES)
        if not request.user.has_perm('stock.add_stock'):
            raise PermissionDenied
        form = StockForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin-stock-list')
        return render(request, 'books/admin/stock_create_or_edit.html', {'form': form})


class AuthorView(View):
    def get(self, request, uuid=None):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        if uuid:
            print("Edit Author")
            instance = get_object_or_404(Author, uuid=uuid)
            form = AuthorForm(instance=instance)
            print(form)
            return render(request, 'books/admin/create_edit/author_create_or_edit.html', {'form': form})

        form = AuthorForm()

        if request.headers.get("X-requested-with") == "XMLHttpRequest":
            html = render_to_string('author/components/author_form.html', {'form': form,
                                                                           'title': 'Author', 'form_type': 'authors'},
                                    request=request)
            return JsonResponse({'html': html})

        print(form)
        return render(request, 'books/admin/create_edit/author_create_or_edit.html', {'form': form})

    def post(self, request, uuid=None):

        if not request.user.is_authenticated:
            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({'error': 'Unauthorized'}, status=401)
            return PermissionDenied
        form = AuthorForm(request.POST, request.FILES)
        if uuid:
            print("Edit Author")
            author = get_object_or_404(Author, uuid=uuid)
            form = AuthorForm(request.POST, request.FILES, instance=author)  # attach instance here
            if form.is_valid():
                form.save()
                return redirect('admin_author_list')
            return render(request, 'books/admin/create_edit/author_create_or_edit.html', {'form': form})

        if form.is_valid():
            author = form.save()

            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "id": author.id,
                    "name": author.name,
                    "message": "Author created successfully"
                })
            return redirect('admin_author_list')

        if request.headers.get("X-requested-with") == "XMLHttpRequest":
            # Re-render form with errors
            html = render_to_string('author/components/author_form.html',
                                    {'form': form, 'title': 'Author', 'form_type': 'authors'},
                                    request=request)
            return JsonResponse({'html': html}, status=400)

        return render(request, 'books/admin/create_edit/author_create_or_edit.html', {'form': form})


class AuthorListView(View):

    def get(self, request):
        authors = (
            Author.objects.all()

        )

        authors = applying_sorting(authors, request, ALLOWED_SORTS["author"])

        paginated_authors, limit = paginate_queryset(request, authors, default_limit=10)

        return render(request, 'books/admin/admin_author_list.html', {
            'paginated_authors': paginated_authors,
            'limit': limit})


# View specific books(Read)
class AuthorDetailView(View):
    def get(self, request, uuid):
        author = get_object_or_404(
            Author,
            uuid=uuid
        )
        print(author)

        print(model_to_dict(author))
        return render(request, 'books/admin/author_detail_view.html', {'author': author})


class PublisherListView(View):

    def get(self, request):
        publisher = (
            Publisher.objects.all()
        )
        # print(publisher.__dict__)
        # See all field names
        print([field.name for field in Publisher._meta.get_fields()])
        # print(model_to_dict(publisher))
        publisher = applying_sorting(publisher, request, ALLOWED_SORTS["publisher"])
        paginated_publisher, limit = paginate_queryset(request, publisher, default_limit=10)

        return render(request, 'books/admin/admin_publisher_list.html', {
            'paginated_publisher': paginated_publisher,
            'limit': limit})


class PublisherDetailView(View):
    def get(self, request, uuid):
        publisher = get_object_or_404(
            Publisher,
            uuid=uuid
        )
        print(publisher)

        print(model_to_dict(publisher))
        return render(request, 'books/admin/publisher_detail_view.html', {'publisher': publisher})


class PublisherView(View):
    def get(self, request, uuid=None):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        if uuid:
            print("Edit Publisher")
            instance = get_object_or_404(Publisher, uuid=uuid)
            form = PublisherForm(instance=instance)
            return render(
                request,
                'books/admin/create_edit/publisher_create_or_edit.html',
                {'form': form}
            )

        form = PublisherForm()

        if request.headers.get("X-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                'author/components/author_form.html',
                {'form': form, 'title': 'Publisher', 'form_type': 'publishers'},
                request=request
            )
            return JsonResponse({'html': html})

        return render(
            request,
            'books/admin/create_edit/publisher_create_or_edit.html',
            {'form': form}
        )

    def post(self, request, uuid=None):
        if not request.user.is_authenticated:
            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({'error': 'Unauthorized'}, status=401)
            return PermissionDenied

        form = PublisherForm(request.POST, request.FILES)

        if uuid:
            print("Edit Publisher")
            publisher = get_object_or_404(Publisher, uuid=uuid)
            form = PublisherForm(request.POST, request.FILES, instance=publisher)
            if form.is_valid():
                form.save()
                return redirect('admin_publisher_list')
            return render(
                request,
                'books/admin/create_edit/publisher_create_or_edit.html',
                {'form': form}
            )

        if form.is_valid():
            publisher = form.save()

            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "id": publisher.id,
                    "name": publisher.name,
                    "message": "Publisher created successfully"
                })
            return redirect('admin_publisher_list')

        if request.headers.get("X-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                'author/components/author_form.html',
                {'form': form, 'title': 'Publisher', 'form_type': 'publishers'},
                request=request
            )
            return JsonResponse({'html': html}, status=400)

        return render(
            request,
            'books/admin/create_edit/publisher_create_or_edit.html',
            {'form': form}
        )


class GenreListView(View):

    def get(self, request):
        genre = (
            Genre.objects.all()
        )
        # print(genre.__dict__)
        # See all field names
        print([field.name for field in Genre._meta.get_fields()])
        # print(model_to_dict(genre))
        genre = applying_sorting(genre, request, ALLOWED_SORTS["genre"])
        paginated_genre, limit = paginate_queryset(request, genre, default_limit=10)

        return render(request, 'books/admin/admin_genre_list.html', {
            'paginated_genre': paginated_genre,
            'limit': limit})


class GenreDetailView(View):
    def get(self, request, uuid):
        genre = get_object_or_404(
            Genre,
            uuid=uuid
        )
        print(genre)

        print(model_to_dict(genre))
        return render(request, 'books/admin/genre_detail_view.html', {'genre': genre})


class GenreView(View):
    def get(self, request, uuid=None):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        print("Uuid from bookview: ", uuid)

        if uuid:
            print("Edit genre")
            genre = get_object_or_404(Genre, uuid=uuid)
            form = GenreForm(instance=genre)
            print(form)
            return render(request, 'books/admin/create_edit/genre_create_or_edit.html', {'form': form})

        form = GenreForm()

        if request.headers.get("X-requested-with") == "XMLHttpRequest":
            html = render_to_string('author/components/author_form.html',
                                    {'form': form, 'title': 'Genre', 'form_type': 'genres'},
                                    request=request)
            return JsonResponse({'html': html})

        print("Create")
        print(form)
        return render(request, 'books/admin/create_edit/genre_create_or_edit.html', {'form': form})

    def post(self, request, uuid=None):
        if not request.user.is_authenticated:
            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({'error': 'Unauthorized'}, status=401)
            return PermissionDenied
        form = GenreForm(request.POST, request.FILES)

        if uuid:
            print("Edit Genre")
            genre = get_object_or_404(Genre, uuid=uuid)
            form = GenreForm(request.POST, request.FILES, instance=genre)  # attach instance here
            if form.is_valid():
                form.save()
                return redirect('admin_genre_list')
            return render(request, 'books/admin/create_edit/genre_create_or_edit.html', {'form': form})

        if form.is_valid():
            genre = form.save()
            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "id": genre.id,
                    "uuid": genre.uuid,
                    "name": genre.name,
                    "message": "Genre created successfully"
                })

            return redirect('admin_genre_list')

        if request.headers.get("X-requested-with") == "XMLHttpRequest":
            # Re-render form with errors
            html = render_to_string('author/components/author_form.html',
                                    {'form': form, 'title': 'Genre', 'form_type': 'genres'},
                                    request=request)
            return JsonResponse({'html': html}, status=400)

        return render(request, 'books/admin/create_edit/genre_create_or_edit.html', {'form': form})
