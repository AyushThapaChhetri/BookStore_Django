import uuid

from django.db import models

from src.core.soft_delete import SafeDeleteModel


class AbstractBaseModel(SafeDeleteModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Set this once when the record is first made.
    updated_at = models.DateTimeField(auto_now=True)  # Update this every time I make any change.

    class Meta:
        abstract = True
