from django.conf import settings
from django.db import models

from src.core.models import AbstractBaseModel


# Create your models here.
class DeliveryInfo(AbstractBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        help_text="User owning the address"
    )
    full_name = models.CharField(max_length=255, help_text="Recipient's full name")
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)  # Optional for countries without states
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='US')  # Default to your primary market
    phone_number = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)  # For quick selection in checkout

    def __str__(self):
        return f"{self.full_name} - {self.street_address}, {self.city}"

    class Meta:
        ordering = ['-is_default', '-created_at']  # Prioritize defaults
