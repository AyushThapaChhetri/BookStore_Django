from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from src.books.forms import BookForm
from src.books.models import Book


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
        limit = request.GET.get('limit', 10)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 10  # fallback to default

        # books = Book.objects.all()
        books = Book.objects.all()

        # Set Up Pagination
        p = Paginator(Book.objects.all(), limit)
        page = request.GET.get('page')
        paginated_books = p.get_page(page)

        return render(request, 'books/book_list.html', {'books': books,
                                                        'paginated_books': paginated_books,
                                                        'limit': limit})


# View specific books(Read)
class BookDetailView(View):
    def get(self, request, uuid):
        book = get_object_or_404(Book, uuid=uuid)
        return render(request, 'books/book_detail_view.html', {'book': book})


# Create a book
class BookCreateView(View):
    def get(self, request):
        form = BookForm()
        return render(request, 'books/book_form.html', {'form': form})

    def post(self, request):
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('book_list')
        return render(request, 'books/book_form.html', {'form': form})


# Update a book
class BookUpdateView(View):
    def get(self, request, uuid):
        print("before permission")
        print(request.user.is_superuser)  # True means has all permissions
        print(request.user.get_all_permissions())  # Shows all assigned permissions
        if not request.user.has_perm('books.change_book'):
            print("between permission")
            raise PermissionDenied  # 403 Forbidden
        print("After permission")
        book = get_object_or_404(Book, uuid=uuid)
        form = BookForm(instance=book)
        return render(request, 'books/book_form.html', {'form': form})

    def post(self, request, uuid):
        print("before permission")
        if not request.user.has_perm('books.change_book'):
            print("between permission")
            raise PermissionDenied  # 403 Forbidden
        print("After permission")
        book = get_object_or_404(Book, uuid=uuid)
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            return redirect('book_list')
        return render(request, 'books/book_form.html', {'form': form})


# Delete a book
class BookDeleteView(View):
    def get(self, request, uuid):
        print("before permission")
        if not request.user.has_perm('books.change_book'):
            print("between permission")
            raise PermissionDenied  # 403 Forbidden
        print("After permission")

        book = get_object_or_404(Book, uuid=uuid)
        return render(request, 'books/book_confirm_delete.html', {'book': book})

    def post(self, request, uuid):
        if not request.user.has_perm('books.change_book'):
            raise PermissionDenied  # 403 Forbidden
        book = get_object_or_404(Book, uuid=uuid)
        # book.delete()
        book.delete(user=request.user)
        return redirect('book_list')
