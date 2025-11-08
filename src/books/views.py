import json
from decimal import Decimal
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
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
from src.books.forms import BookForm, AuthorForm, GenreForm, PublisherForm
from src.books.models import Book, Author, Publisher, Genre
from src.books.pagination import paginate_queryset
from src.books.utils import searchfilter_bookStore, search_query
from src.cart.models import CartItem, Cart
from src.cart.utils import calculate_cart_totals, round_decimal
from src.orders.models import Order, OrderItem
from src.shipping.forms import DeliveryForm
from src.shipping.models import DeliveryInfo
from src.stock.forms import StockForm
from src.stock.models import Stock
from src.stock.services import StockService


# Create your views here.
def hello(request):
    return render(request, 'books/hello.html', {'name': 'Ayush'})


def search_books(request):
    query = request.GET.get('q', '').strip()

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
                'price': float(book.stock.current_price),
                "stock_quantity": book.stock.total_remaining_quantity,
                "is_available": book.stock.is_available,
                "discount_percentage": float(book.stock.current_discount_percentage),
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

    print("Hello1")
    print(book_uuid)
    # book = get_object_or_404(Book, uuid=book_uuid)
    book = get_object_or_404(
        Book.objects.select_related('stock')
        .prefetch_related('stock__batches')
        .annotate(
            total_quantity=Coalesce(Sum('stock__batches__remaining_quantity'), 0)
        ),
        uuid=book_uuid
    )
    print("Hello")
    # if book.stock.stock_quantity <= 0:
    if book.total_quantity <= 0:
        print("cannot")
        return JsonResponse({'success': False, 'message': f"'{book.title}' is sold out"}, status=400)

    print("hi")
    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)

    cart_item.unit_price = book.stock.current_price

    cart_item.discount_amount = book.stock.current_discount_percentage

    if created:

        message = f"{book.title} added to cart"
    else:

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

        if action == 'increment':
            if item.quantity >= book.stock.total_remaining_quantity:

                quantity = book.stock.total_remaining_quantity
                message = f"Only {book.stock.total_remaining_quantity} left in stock."
            else:
                quantity = item.quantity + 1


        elif action == 'decrement':
            if item.quantity <= 1:
                quantity = 1
                message = "Quantity cannot be less than 1."
            else:
                quantity = item.quantity - 1

        if quantity > book.stock.total_remaining_quantity:
            quantity = max(book.stock.total_remaining_quantity, 1)
            message = f"Stock updated. Only {book.stock.total_remaining_quantity} left now."

        item.quantity = quantity
        item.save()

        totals = calculate_cart_totals(request.user)
        print(totals)
        response = {
            "success": True,
            "quantity": item.quantity,
            "subtotal": item.cart.get_total_price,
            "available_stock": book.stock.total_remaining_quantity,
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


class BookListView(View):

    def get(self, request):
        books = (
            Book.objects.all()
            .select_related('publisher', 'stock')
            .prefetch_related('authors', 'genres')
        )

        books = applying_sorting(books, request=request, allowed_sorts=ALLOWED_SORTS["book"])

        paginated_books, limit = paginate_queryset(request, books, default_limit=10)

        return render(request, 'books/admin/admin_book_list.html', {'books': books,
                                                                    'paginated_books': paginated_books,
                                                                    'limit': limit,
                                                                    'add_perm': "book.add_book",
                                                                    "sort": request.GET.get("sort", "created_desc"),
                                                                    })


class BookRecycleBinListView(View):
    def get(self, request):
        books = Book.deleted_objects.all().select_related('publisher', 'stock').prefetch_related('authors', 'genres')
        # print('Recycled', books)
        books = applying_sorting(books, request, allowed_sorts=ALLOWED_SORTS["book"])
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


class StockListView(View):

    def get(self, request):
        stocks = (
            Stock.objects.all()
            .select_related('book').annotate(
                total_quantity=Coalesce(Sum('batches__remaining_quantity'), 0)
            )

        )

        print("stocks", stocks)
        print([f.column for f in Stock._meta.get_fields() if hasattr(f, 'column')])

        stocks = applying_sorting(stocks, request, allowed_sorts=ALLOWED_SORTS["stock"])

        paginated_stocks, limit = paginate_queryset(request, stocks, default_limit=10)

        return render(request, 'books/admin/admin_stock_list.html', {'stocks': stocks,
                                                                     'paginated_stocks': paginated_stocks,

                                                                     'limit': limit})


class BookDetailView(View):
    def get(self, request, uuid):
        book = get_object_or_404(
            Book.objects.select_related("publisher", "stock").prefetch_related("authors", "genres"),
            uuid=uuid
        )
        return render(request, 'books/admin/book_detail_view.html', {'book': book})


class StockDetailView(View):
    def get(self, request, uuid):
        stock = get_object_or_404(
            Stock.objects.select_related("book"),
            uuid=uuid
        )
        return render(request, 'books/admin/stock_detail_view.html', {'stock': stock})


@method_decorator(never_cache, name='dispatch')
class BookStore(View):
    def get(self, request, price_aggregate=None):
        query = request.GET.get('q', '')
        # print('hello')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort_by = request.GET.get('sort')

        # print("AJAX request?", request.headers.get("x-requested-with"))

        # print('query sent store:', query)
        # print('min_price store:', min_price)
        # print('max_price store:', max_price)
        # print('sort_by store:', sort_by)

        # books = Book.objects.all()
        # start with Book queryset
        # books = Book.objects.all().annotate(
        #     price=F('stock__price'),
        #     stock_quantity=F('stock__stock_quantity'),
        #     is_available=F('stock__is_available'),
        #     last_restock_date=F('stock__last_restock_date')
        # )
        # books = Book.objects.all().annotate(
        #     price=F('stock__current_price'),
        #     stock_quantity=Coalesce(Sum('stock__batches__remaining_quantity'), 0),
        #     is_available=F('stock__is_available'),
        #     last_restock_date=F('stock__last_restock_date')
        # )
        books = Book.objects.select_related('stock').prefetch_related('stock__batches').annotate(
            total_quantity=Coalesce(Sum('stock__batches__remaining_quantity'), 0)
        )
        # for book in books:
        #     print(book.stock.current_price)
        #     print(book.stock.total_remaining_quantity)

        items_count = CartItem.objects.filter(cart__user=request.user).count()
        print(items_count, ": Item count")

        books, min_price_value, max_price_value, db_max = searchfilter_bookStore(books, query, min_price,
                                                                                 max_price, sort_by)

        paginated_books, limit = paginate_queryset(request, books, default_limit=12)

        # print("Paginated_books: ", paginated_books)

        query_params = request.GET.copy()
        # print("query_params book store bata: ", query_params)

        if 'page' in query_params:
            query_params.pop('page')

        for key in list(query_params.keys()):
            if all(v == "" for v in query_params.getlist(key)):
                query_params.pop(key)

        # print("query_params book store bata after: ", query_params)

        context = {
            'books': books,
            'paginated_books': paginated_books,
            'limit': limit,
            'min_price_value': min_price_value,
            'max_price_value': max_price_value,
            'query_string': query_params.urlencode(),  # for pagination links

        }

        # print("db max:", db_max)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # print("hello from headers")
            cards_html = render_to_string("books/components/book_cards.html", {'paginated_books': paginated_books, })
            pagination_html = render_to_string('books/components/pagination_div.html',
                                               {'paginated_books': paginated_books,
                                                "query_string": query_params.urlencode(), 'is_ajax_page': True,
                                                'limit': limit, })

            return JsonResponse({
                "cards": cards_html,
                "pagination": pagination_html,
                'items_count': items_count,
                'search_min_price_limit': 0,
                'search_max_price_limit': db_max,
                "min_price": min_price_value,
                "max_price": max_price_value,

            })

        return render(request, 'books/book_store.html', context)


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

        delivery_uuid = request.session.get('delivery_uuid')
        print(delivery_uuid, ' : Delivery UUID')
        if delivery_uuid:
            delivery_instance = DeliveryInfo.objects.filter(
                uuid=delivery_uuid,
                user=request.user
            ).first()

        # Session missing cha vane, fallback to latest delivery
        if not delivery_instance:
            delivery_instance = DeliveryInfo.objects.filter(user=request.user).order_by('-created_at').first()

        form = DeliveryForm(instance=delivery_instance)

        cart = Cart.objects.get_or_create(user=request.user)[0]
        items = cart.items.all()
        stock_adjusted = False

        for item in items:
            if item.quantity > item.book.stock.total_remaining_quantity:
                item.quantity = max(item.book.stock.total_remaining_quantity, 1)  # keep at least 1
                item.save()
                stock_adjusted = True
                messages.warning(
                    request,
                    f"{item.book.title} quantity adjusted to {item.quantity} due to stock limits."
                )

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
            messages.error(request, 'Please Select Payment Options')
            return redirect('book_payment')

        redirect_response = is_cart_item_exists(request)
        if redirect_response:
            return redirect_response

        delivery_uuid = request.session.get('delivery_uuid')
        delivery_instance = None
        if delivery_uuid:
            delivery_instance = DeliveryInfo.objects.filter(uuid=delivery_uuid, user=request.user).first()

        if not delivery_instance:
            delivery_instance = request.user.addresses.order_by('-created_at').first()

        cart_totals = calculate_cart_totals(request.user)
        cart = cart_totals['cart']
        items = cart_totals["items"]

        total_amount = cart.total_after_discount_shipping
        shopping_cost = cart.shipping_cost
        try:
            with transaction.atomic():

                for item in items:
                    stock = item.book.stock
                    if item.quantity > stock.total_remaining_quantity:
                        messages.error(request, f"Not enough stock for {item.book.title}")
                        return redirect('book_cart')

                order = Order.objects.create(
                    user=request.user,
                    status='pending',
                    total_amount=total_amount,
                    shipping_address=delivery_instance,
                    shipping_cost=shopping_cost,
                )

                request.session['order_uuid'] = str(order.uuid)

                for item in items:
                    order_item = OrderItem.objects.create(
                        order=order,
                        book=item.book,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        discount_amount=item.discount_amount,
                    )

                    print("Hi")

                    StockService.reserve_for_order(order_item, changed_by=request.user)

                cart.items.all().delete()

                if delivery_uuid:
                    del request.session['delivery_uuid']

                messages.success(request, "Order Successful")

        except ValueError as ve:

            messages.error(request, str(ve))
            return redirect('book_cart')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            print(e)
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

            'subtotal': round_decimal(subtotal),
            'discount': round_decimal(discount),
            'total_price': round_decimal(total_price),

        })


@method_decorator(never_cache, name='dispatch')
class BookCart(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')

        totals = calculate_cart_totals(request.user)

        return render(request, 'books/book_cart.html',

                      totals
                      )


@method_decorator(never_cache, name='dispatch')
class BookDetailStore(View):
    def get(self, request, uuid):
        # book = get_object_or_404(Book, uuid=uuid)

        book = get_object_or_404(
            Book.objects.select_related('stock')
            .prefetch_related('stock__batches')
            .annotate(
                total_quantity=Coalesce(Sum('stock__batches__remaining_quantity'), 0)
            ),
            uuid=uuid
        )
        cart = Cart.objects.get_or_create(user=request.user)[0]

        book_in_cart = CartItem.objects.filter(cart=cart, book=book).first()

        quantity = book_in_cart.quantity if book_in_cart else 1

        cart_item_uuid = str(book_in_cart.uuid) if book_in_cart else None
        # print('Cart uuid from detail store: ', cart_item_uuid)

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

                    book.refresh_from_db()

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
        print('Post from authors')
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
            print("author to be saved from the forntend popup")
            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "id": author.id,
                    "name": author.name,
                    "message": "Author created successfully"
                })
            return redirect('admin_author_list')

        else:
            print("Errors:", form.errors)

        if request.headers.get("X-requested-with") == "XMLHttpRequest":
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

        authors = applying_sorting(authors, request, allowed_sorts=ALLOWED_SORTS["author"])

        paginated_authors, limit = paginate_queryset(request, authors, default_limit=10)

        return render(request, 'books/admin/admin_author_list.html', {
            'paginated_authors': paginated_authors,
            'limit': limit})


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

        print([field.name for field in Publisher._meta.get_fields()])

        publisher = applying_sorting(publisher, request, allowed_sorts=ALLOWED_SORTS["publisher"])
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
        print('publisher 3')
        if form.is_valid():
            publisher = form.save()

            print('publisher 4')
            if request.headers.get("X-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "id": publisher.id,
                    "name": publisher.name,
                    "message": "Publisher created successfully"
                })
            return redirect('admin_publisher_list')

        print('publisher 2')
        if request.headers.get("X-requested-with") == "XMLHttpRequest":
            print('publisher 1')
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

        print([field.name for field in Genre._meta.get_fields()])
        # print(model_to_dict(genre))
        genre = applying_sorting(genre, request, allowed_sorts=ALLOWED_SORTS["genre"])
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
            print('genre ajax')
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
            html = render_to_string('author/components/author_form.html',
                                    {'form': form, 'title': 'Genre', 'form_type': 'genres'},
                                    request=request)
            return JsonResponse({'html': html}, status=400)

        return render(request, 'books/admin/create_edit/genre_create_or_edit.html', {'form': form})


def field_options(request, field_name):
    print("hello")
    if field_name == "authors":
        print("author")
        queryset = Author.objects.values_list("id", "name")
    elif field_name == "publisher":
        print("publisher")
        queryset = Publisher.objects.values_list("id", "name")
    elif field_name == "genres":
        print("genres")
        queryset = Genre.objects.values_list("id", "name")
    else:
        return JsonResponse({"html": ""}, status=400)

    is_multiple = field_name in ["genres", "authors"]

    selected = request.GET.getlist("selected[]", [])  # or []

    if not is_multiple and selected:
        selected = [selected[-1]]

    selected = [int(x) for x in selected if x.isdigit()]

    html = render_to_string(
        "author/components/field_options.html",
        {"choices": queryset, "selected_values": selected, "is_multiple": is_multiple}
    )

    return JsonResponse({"html": html})
