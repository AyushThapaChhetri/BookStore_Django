from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from src.users.form import UserForm, LoginForm
from django.views import View


# Create your views here.
class UserCreateView(View):
    def get(self, request):
        form = UserForm()
        return render(request, '../../Project_B/templates/users/signup_users_form.html', {'form': form})

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
            return render(request, '../../Project_B/templates/users/signup_users_form.html', {'form': form})

class UserLoginView(View):
    def get(self, request):
        form = LoginForm()
        return render(request, '../../Project_B/templates/users/login_users_form.html', {'form': form})

    def post(self, request):
            form = LoginForm(request.POST)
            if form.is_valid():
               email = form.cleaned_data.get('email')
               password = form.cleaned_data.get('password')
               user = authenticate(request, email=email, password=password)
               if user is not None:
                   login(request, user)
                   return redirect('book_list')
               else:
                   form.add_error(None,'Invalid email or password')
            return render(request, '../../Project_B/templates/users/login_users_form.html', {'form': form})
