import uuid

from django.db import models

from src.core.soft_delete import SafeDeleteModel


class AbstractBaseModel(SafeDeleteModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
