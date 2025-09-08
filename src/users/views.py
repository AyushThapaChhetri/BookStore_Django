from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View

from src.users.form import UserForm, LoginForm, SetPasswordForm
from .models import User
from .task import send_activation_email
from .utils import AccountActivationTokenGenerator


# Create your views here.
class UserCreateView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = UserForm()
        return render(request, 'users/signup_users_form.html', {'form': form})

    # def post(self, request):
    #     form = UserForm(request.POST, request.FILES)
    #     if form.is_valid():
    #         print('before validation')
    #         form.save()
    #         print('after validation')
    #         return redirect('book_list')
    #     print('not valid')
    #     # Optionally, print form errors to debug:
    #     print(form.errors)
    #     return render(request, 'users/signup_users_form.html', {'form': form})
    def post(self, request):
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_unusable_password()
                    user.is_active = False
                    user.save()

                    # Try enqueue task
                    try:
                        send_activation_email.delay(user.email)
                    except Exception as e:
                        # Log the error but don't prevent signup
                        print("Could not enqueue activation email:", e)

                return redirect('password_reset_done')
            except Exception as e:
                # rollback happens automatically
                form.add_error(None, "Could not send activation email. Please try again later.")
                print("Error during signup:", e)
        # Optionally, print form errors to debug:
        print(form.errors)
        return render(request, 'users/signup_users_form.html', {'form': form})


def activate(request, uidb64, token):
    token_generator = AccountActivationTokenGenerator()
    actual_user = request.user
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        print("UID:", uid, "Token:", token)
        print("User:", user)
        if actual_user.is_authenticated:
            print('User is already authenticated.', user)
            messages.error(request, 'Account is logged in. Please Logout First!')
            return redirect('home')

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not token_generator.check_token(user, token):
        if user:
            user.delete()
        messages.error(request, 'Invalid or expired link. Please signup again.')
        return redirect('signup_view')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        print("Form created for user:", user.email)

        if form.is_valid():
            form.save()
            user.is_active = True
            user.save()
            messages.success(request, 'Account activated. Log in now.')
            return redirect('login_view')  # make sure URL name matches
    else:
        form = SetPasswordForm(user)

    return render(request, 'users/password_set.html', {'form': form})


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
            try:
                user_obj = User.objects.get(email=email)
            except User.DoesNotExist:
                user_obj = None

                # Check if user exists and has usable password
            if user_obj:
                if not user_obj.has_usable_password() and not user_obj.is_active:
                    messages.error(request, 'Account is not registered yet.Please check your email.')
                    return render(request, 'users/login_users_form.html', {'form': form})

                # Now authenticate only if password is usable
                user = authenticate(request, email=email, password=password)
                if user:
                    login(request, user)
                    messages.success(request, "Login successful!")
                    return redirect('home')
                else:
                    messages.error(request, "Invalid email or password.")
                    return render(request, 'users/login_users_form.html', {'form': form})
            else:
                messages.error(request, "Invalid email or password.")
                return render(request, 'users/login_users_form.html', {'form': form})

                # If form invalid
        messages.error(request, 'Please correct the form')
        return render(request, 'users/login_users_form.html', {'form': form})
        #     try:
        #         print('h1')
        #         inactiveuser_detail = User.objects.get(email=email)
        #         print('h2')
        #         if not inactiveuser_detail.has_usable_password() and not inactiveuser_detail.is_active:
        #             print('h3')
        #             messages.error(request, 'Account is not Registered yet, Please Check your Email')
        #             print('h4')
        #     except User.DoesNotExist:
        #         user_obj = None
        #
        #     user = authenticate(request, email=email, password=password)
        #     if user is not None:
        #         login(request, user)
        #         messages.success(request, "Login successful!")
        #         return redirect('home')
        #     else:
        #         messages.error(request, "Invalid email or password.")
        #
        #         return render(request, 'users/login_users_form.html', {'form': form})
        #
        # print(form.errors)
        #
        # messages.error(request, 'Please correct the form')
        #
        # return render(request, 'users/login_users_form.html', {'form': form})


class UserLogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Logout successful!")
        return redirect('login_view')
