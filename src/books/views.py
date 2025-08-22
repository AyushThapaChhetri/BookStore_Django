import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from pygments.lexers import q

from src.books.forms import BookForm
from src.books.models import Book
from src.books.pagination import paginate_queryset
from src.cart.models import CartItem, Cart
from src.orders.models import Order, OrderItem
from src.shipping.forms import DeliveryForm
from src.shipping.models import DeliveryInfo


# Create your views here.
def hello(request):
    # return render(request, '../../Project_B/templates/books/hello.html', {'name': 'Ayush'})
    return render(request, 'books/hello.html', {'name': 'Ayush'})
    # return render(request, 'hello.html')
    # return HttpResponse("Hello, %s!" % request.path)


def search_books(request):
    query = request.GET.get('q', '').strip()
    books = Book.objects.filter(
        Q(title__icontains=query) |
        Q(author__icontains=query) |
        Q(publisher__icontains=query)
    )

    data = list(books.values(
        'uuid', 'title', 'author', 'publisher', 'description',
        'pages', 'language', 'created_at', 'updated_at'
    ))
    return JsonResponse({'books': data})


@require_POST
@login_required
def add_to_cart(request):
    book_uuid = request.POST.get('book_uuid')
    if not book_uuid:
        return JsonResponse({'success': False, 'message': 'No book uuid provided'}, status=400)

    book = get_object_or_404(Book, uuid=book_uuid)

    if book.stock_quantity <= 0:
        return JsonResponse({'success': False, 'message': f"'{book.title}' is sold out"}, status=400)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    print(cart)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    print(cart_item)
    if created:
        # First Time
        message = f"{book.title} added to cart"
    else:
        # Already in cart
        message = f"{book.title} is already on cart"

    return JsonResponse({
        'success': True,
        'created': created,
        'message': f"{book.title} added to cart",
        'quantity': cart_item.quantity,
        'total_price': cart.get_total_price(),
        'cart_items_count': cart.items.count()
    })


@require_POST
@login_required
def update_cart(request, item_uuid):
    data = json.loads(request.body)
    quantity = int(data.get('quantity', 1))
    action = str(data.get('action', ''))

    try:
        item = CartItem.objects.get(uuid=item_uuid, cart__user=request.user)
        book = item.book
        message = None

        # Handle increment
        if action == 'increment':
            if item.quantity >= book.stock_quantity:
                # Can't go above stock
                quantity = book.stock_quantity
                message = f"Only {book.stock_quantity} left in stock."
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
        if quantity > book.stock_quantity:
            quantity = max(book.stock_quantity, 1)
            message = f"Stock updated. Only {book.stock_quantity} left now."

        item.quantity = quantity
        item.save()

        cart = Cart.objects.get_or_create(user=request.user)[0]
        total_price = sum(i.get_subtotal() for i in cart.items.all())

        response = {
            "success": True,
            "quantity": item.quantity,
            "subtotal": item.get_subtotal(),
            "total_price": total_price,
            "available_stock": book.stock_quantity,
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
        books = Book.objects.all().order_by('-created_at')
        paginated_books, limit = paginate_queryset(request, books, default_limit=10)

        return render(request, 'books/book_list.html', {'books': books,
                                                        'paginated_books': paginated_books,
                                                        'limit': limit})


# View specific books(Read)
class BookDetailView(View):
    def get(self, request, uuid):
        book = get_object_or_404(Book, uuid=uuid)
        return render(request, 'books/book_detail_view.html', {'book': book})


class BookStore(View):
    def get(self, request):
        query = request.GET.get('q', '')
        books = Book.objects.all()

        if query:
            books = books.filter(
                Q(title__icontains=query) |
                Q(author__icontains=query) |
                Q(publisher__icontains=query)
            )
        #
        # books = Book.objects.all().order_by('-created_at')
        paginated_books, limit = paginate_queryset(request, books, default_limit=12)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            cards_html = render_to_string("books/components/book_cards.html", {'paginated_books': paginated_books, })
            pagination_html = render_to_string('books/components/pagination_div.html',
                                               {'paginated_books': paginated_books})

            return JsonResponse({
                "cards": cards_html,
                "pagination": pagination_html,
            })

            # return render(request, "books/components/book_cards.html", {
            #     "paginated_books": paginated_books,
            #     "limit": limit
            # })

        return render(request, 'books/book_store.html', {'books': books,
                                                         'paginated_books': paginated_books,
                                                         'limit': limit})

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
            if item.quantity > item.book.stock_quantity:
                item.quantity = max(item.book.stock_quantity, 1)  # keep at least 1
                item.save()
                stock_adjusted = True
                messages.warning(
                    request,
                    f"{item.book.title} quantity adjusted to {item.quantity} due to stock limits."
                )

        total_price = sum(item.get_subtotal() for item in items)
        total_quantity = cart.items.aggregate(Sum('quantity'))[
                             'quantity__sum'
                         ] or 0
        # print("Form")
        # print(form)
        return render(request, 'books/book_checkout.html',
                      {'form': form, 'total_price': total_price, 'total_quantity': total_quantity})

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

        cart = Cart.objects.get_or_create(user=request.user)[0]
        items = cart.items.all()
        total_quantity = cart.items.aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_price = sum(item.get_subtotal() for item in items)
        return render(request, 'books/book_payment.html', {'delivery': delivery_instance,
                                                           'total_price': total_price,
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

        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.all()
        total_amount = sum(item.get_subtotal() for item in items)

        try:
            with transaction.atomic():
                locked_books = {}
                for item in items:
                    book = Book.objects.select_for_update().get(id=item.book.id)
                    if item.quantity > book.stock_quantity:
                        messages.error(request, f"Not enough stock for {book.title}")
                        return redirect('book_cart')
                    locked_books[item.book.id] = book
                order = Order.objects.create(
                    user=request.user,
                    status='pending',
                    total_amount=total_amount,
                    shipping_address=delivery_instance,
                    shipping_cost=0,
                )

                request.session['order_uuid'] = str(order.uuid)

                for item in items:
                    # book = Book.objects.select_for_update().get(id=item.book.id)
                    book = locked_books[item.book.id]
                    OrderItem.objects.create(
                        order=order,
                        book=item.book,
                        quantity=item.quantity,
                        unit_price=item.book.price,
                    )

                    # Reduce stock
                    book.stock_quantity -= item.quantity
                    book.save()

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
        return render(request, 'books/order_complete.html', {
            'order': order,
            'order_items': order_items,
        })


@method_decorator(never_cache, name='dispatch')
class BookCart(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')

        cart = Cart.objects.get_or_create(user=request.user)[0]
        items = cart.items.all()
        items_count = cart.items.count()
        total_quantity = cart.items.aggregate(Sum('quantity'))[
                             'quantity__sum'
                         ] or 0

        total_price = sum(item.get_subtotal() for item in items)

        return render(request, 'books/book_cart.html',
                      {'cart': cart, 'items': items, 'items_count': items_count, 'total_quantity': total_quantity,
                       'total_price': total_price})


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

        return render(request, 'books/book_detail_store.html',
                      {'books': book, 'book_in_cart': book_in_cart, 'quantity': quantity,
                       'cart_item_uuid': cart_item_uuid, })


class BookView(View):
    def get(self, request, uuid=None):
        form = BookForm()
        if uuid:
            print("Edit")
            book = get_object_or_404(Book, uuid=uuid)
            form = BookForm(instance=book)
            return render(request, 'books/book_form.html', {'form': form})
        print("Create")
        return render(request, 'books/book_form.html', {'form': form})

    def post(self, request, uuid=None):
        print("Create Post before")
        if uuid and 'delete' in request.POST:
            print("Delete")
            if not request.user.has_perm('books.delete_book'):
                raise PermissionDenied
            book = get_object_or_404(Book, uuid=uuid)
            book.delete(user=request.user)
            return redirect('book_list')

        # Edit
        if uuid:
            print("Edit")
            if not request.user.has_perm('books.change_book'):
                raise PermissionDenied
            book = get_object_or_404(Book, uuid=uuid)
            form = BookForm(request.POST, request.FILES, instance=book)  # attach instance here
            if form.is_valid():
                form.save()
                return redirect('book_list')
            return render(request, 'books/book_form.html', {'form': form})

        # Create
        print("Create Post After")
        print(request.FILES)
        if not request.user.has_perm('books.add_book'):
            raise PermissionDenied
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('book_list')
        return render(request, 'books/book_form.html', {'form': form})
