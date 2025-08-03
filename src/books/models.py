from django.db import models
import uuid
from src.core.models import AbstractBaseModel


# Create your models here.
class Book(AbstractBaseModel):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    publisher = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    pages = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=100)
    # copies = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title