from django.shortcuts import redirect, render
from django.views import View

from src.shipping.forms import DeliveryForm


# Create your views here.
class DeliverInfoView(View):

    def post(self, request):
        print("Create Post before")

        form = DeliveryForm()
        if form.is_valid():
            form.save()
            return redirect('book_payment')

        return render(request, 'books/book_checkout.html', {'form': form})
