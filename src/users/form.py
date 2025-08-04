from django import forms
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm

from src.users.models import User

class UserForm(UserCreationForm):
    # confirmPassword = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password1',
            # 'confirmPassword',
            'password2',
            'contact_number',
            'date_of_birth',
            'address',
            'profile_picture',
        ]
        widgets = {
            # 'password' : forms.PasswordInput(),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > timezone.localdate():
            raise forms.ValidationError("Date of Birth cannot be in the future.")
        return dob

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if contact_number is not None:
            return contact_number.strip() or None
        return None

    def clean_address(self):
        address = self.cleaned_data.get('address','')
        return address.strip() or None

    def clean_profile_picture(self):
        profile_picture = self.cleaned_data.get('profile_picture')
        return profile_picture or None



class LoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'email',
            'password',
        ]