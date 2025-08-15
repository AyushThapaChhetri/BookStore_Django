from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from src.books.forms import BookForm
from src.books.models import Book
from src.books.pagination import paginate_queryset


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
        return render(request, 'books/book_checkout.html')


class BookCheckoutPayment(View):
    def get(self, request):
        return render(request, 'books/book_payment.html')


class BookOrderComplete(View):
    def get(self, request):
        return render(request, 'books/order_complete.html')


class BookCart(View):
    def get(self, request):
        return render(request, 'books/book_cart.html')


class BookDetailStore(View):
    def get(self, request, uuid):
        book = get_object_or_404(Book, uuid=uuid)
        return render(request, 'books/book_detail_store.html', {'books': book})


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
            form = BookForm(request.POST, instance=book)  # ✅ attach instance here
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

    # def put(self, request, uuid):
    #     print("delete_book")
    #     if not request.user.has_perm('books.change_book'):
    #         raise PermissionDenied
    #     book = get_object_or_404(Book, uuid=uuid)
    #     form = BookForm(request.POST, instance=book)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('book_list')
    #     return render(request, 'books/book_form.html', {'form': form})
    #
    # def delete(self, request, uuid):
    #     print("delete_book")
    #     if not request.user.has_perm('books.delete_book'):
    #         raise PermissionDenied
    #     book = get_object_or_404(Book, uuid=uuid)
    #     book.delete(user=request.user)
    #     return redirect('book_list')
