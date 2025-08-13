from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views import View

from src.users.form import UserForm, LoginForm


# Create your views here.
class UserCreateView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = UserForm()
        return render(request, 'users/signup_users_form.html', {'form': form})

    def post(self, request):
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            print('before validation')
            form.save()
            print('after validation')
            return redirect('book_list')
        print('not valid')
        # Optionally, print form errors to debug:
        print(form.errors)
        return render(request, 'users/signup_users_form.html', {'form': form})


class UserLoginView(View):
    def get(self, request):

        if request.user.is_authenticated:
            return redirect('home')
        form = LoginForm()
        return render(request, 'users/login_users_form.html', {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Login successful!")
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
                return redirect('login_view')
                # form.add_error(None,'Invalid email or password')
        print(form.errors)
        # return render(request, 'users/login_users_form.html', {'form': form})
        messages.error(request, 'Please correct the form')
        return redirect('login_view')


class UserLogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Logout successful!")
        return redirect('login_view')
