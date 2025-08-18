from django import forms

from src.shipping.models import DeliveryInfo


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = DeliveryInfo
        fields = [
            'full_name',
            'country',
            'street_address',
            'city',
            'state',
            'zip_code',
            'phone_number',
        ]

    def clean_state(self):
        state = self.cleaned_data.get('state', '')
        return state.strip() if state else None
