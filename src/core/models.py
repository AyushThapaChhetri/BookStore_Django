import uuid

from django.db import models

from src.core.soft_delete import SafeDeleteModel


# Custom manager to exclude soft-deleted items by default.
# class BaseManger(models.Manager):
#     # overrides Django's built-in method called get_queryset()
#     def get_queryset(self):
#         # only return rows where deleted_at is NULL(i.e., not deleted).
#         return super().get_queryset().filter(deleted_at__isnull=True)


# class AbstractBaseModel(models.Model):
#     uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     deleted_at = models.DateTimeField(blank=True, null=True)
#
#     objects = BaseManger() # Default manager excludes soft-deleted items
#     all_objects = models.Manager()  # Access all items, including deleted ones
#
#     def delete(self, *args, **kwargs):
#         """Soft delete by setting deleted_at"""
#         self.deleted_at = timezone.now()
#         self.save()
#
#     def restore(self):
#         """Restore by clearing deleted_at"""
#         self.deleted_at = None
#         self.save()
#     class Meta:
#         abstract = True #This model won't create a database table


class AbstractBaseModel(SafeDeleteModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
