import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
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
    print("update start")
    print(item_uuid)
    if request.method == 'POST':
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        print("Inside if")
        try:
            print("Inside if 1")
            print("User:", request.user)
            item = CartItem.objects.get(uuid=item_uuid, cart__user=request.user)
            print("Item found:", item)
            book = item.book
            print("Book:", book)
            if quantity > book.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'error': f"Only {book.stock_quantity} left in stock."
                }, status=400)

            if quantity < 1:
                quantity = 1

            item.quantity = quantity
            item.save()

            cart = Cart.objects.get_or_create(user=request.user)[0]
            items = cart.items.all()
            total_price = sum(item.get_subtotal() for item in items)
            return JsonResponse({
                "success": True,
                "quantity": item.quantity,
                "subtotal": item.get_subtotal(),
                'total_price': total_price,
                "available_stock": book.stock_quantity
            })

        except CartItem.DoesNotExist:
            print("CartItem not found!")
            return JsonResponse({"success": False, "error": "Item not found"}, status=404)


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
        paginated_books, limit = paginate_queryset(request, books)

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
        books = Book.objects.all()
        #
        # books = Book.objects.all().order_by('-created_at')
        paginated_books, limit = paginate_queryset(request, books)

        return render(request, 'books/book_store.html', {'books': books,
                                                         'paginated_books': paginated_books,
                                                         'limit': limit})

        # return render(request, 'books/book_store.html', context)


class BookCheckout(View):
    def get(self, request):
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

        cart = Cart.objects.get_or_create(user=request.user)[0]
        items = cart.items.all()
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
        delivery_uuid = request.session.get('delivery_uuid')
        delivery_instance = None

        if delivery_uuid:
            try:
                delivery_instance = DeliveryInfo.objects.get(uuid=delivery_uuid, user=request.user)
            except DeliveryInfo.DoesNotExist:
                delivery_instance = None

        if not delivery_instance:
            delivery_instance = request.user.addresses.order_by('-created_at').first()

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

        cart = Cart.objects.get(user=request.user)
        items = cart.items.all()
        if not items:
            return redirect('book_cart')

        delivery_uuid = request.session.get('delivery_uuid')
        delivery_instance = None
        if delivery_uuid:
            delivery_instance = DeliveryInfo.objects.filter(uuid=delivery_uuid, user=request.user).first()
        if not delivery_instance:
            delivery_instance = request.user.addresses.order_by('-created_at').first()

        total_amount = sum(item.get_subtotal() for item in items)
        order = Order.objects.create(
            user=request.user,
            status='pending',
            total_amount=total_amount,
            shipping_address=delivery_instance,
            shipping_cost=0,
        )

        request.session['order_uuid'] = str(order.uuid)

        for item in items:
            OrderItem.objects.create(
                order=order,
                book=item.book,
                quantity=item.quantity,
                unit_price=item.book.price,
            )

            # Reduce stock
            item.book.stock_quantity -= item.quantity
            item.book.save()

        cart.items.all().delete()
        order_items = order.items.all()
        return render(request, 'books/order_complete.html',
                      {'order': order, 'payment_method': payment_method, 'order_items': order_items})


class BookOrderComplete(View):
    def get(self, request):
        order_uuid = request.session.get('order_uuid')
        if not order_uuid:
            return redirect('book_cart')

        order = Order.object.get(uuid=order_uuid, user=request.user).first()
        if not order:
            return redirect('book_cart')

        order_items = order.items.all()
        return render(request, 'books/order_complete.html', {
            'order': order,
            'order_items': order_items,
        })


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
            form = BookForm(request.POST, instance=book)  # attach instance here
            if form.is_valid():
                form.save()
                return redirect('book_list')
            return render(request, 'books/book_form.html', {'form': form})

        # Create
        print("Create Post After")
        if not request.user.has_perm('books.add_book'):
            raise PermissionDenied
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('book_list')
        return render(request, 'books/book_form.html', {'form': form})
