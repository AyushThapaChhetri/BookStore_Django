from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


# User = get_user_model()
def get_user():
    return get_user_model()


class SafeDeleteQuerySet(models.QuerySet):
    """
        Custom QuerySet that provides soft delete functionality.
        This extends Django's default QuerySet with methods for soft delete, hard delete, etc.
        """

    def delete(self):
        """
                Soft delete all objects in the queryset by setting the 'deleted' timestamp.
                Instead of removing records, it updates them to mark as deleted.
                """
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """
                Permanently delete objects from the database.
                This calls the superclass's delete() to actually remove records.
                """
        return super().delete()

    def active(self):
        """
                Return only non-deleted objects.
                Filters where 'deleted' is NULL.
                """

        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """
                Return only deleted objects.
                Filters where 'deleted' is not NULL.
                """
        return self.filter(deleted_at__isnull=True)

    def restore(self):
        """
                Restore deleted objects by setting 'deleted' field to None.
                Also clears 'deleted_by' if set.
                """
        return self.filter(deleted_at=None, deleted_by=None)
