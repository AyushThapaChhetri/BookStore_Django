from django.db import models
from django.utils import timezone

from src.core.managers import ActiveObjectsManager, DeletedObjectsManager, AllObjectsManager


# from src.users.models import User


class SafeDeleteModel(models.Model):
    """
        Abstract base class that provides soft delete functionality with three managers.

        Managers:
        - objects: Only active (non-deleted) objects (default manager)
        - all_objects: All objects (active + deleted)
        - deleted_objects: Only deleted objects

        All managers inherit from BaseSafeDeleteManager and have access to all methods.
        """

    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when this object was deleted",
                                      db_index=True)

    # deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
    #                                related_name="%(app_label)s_%(class)s_deleted_set",
    #                                help_text="User who deleted this object")
    deleted_by = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="%(app_label)s_%(class)s_deleted_set",
                                   help_text="User who deleted this object")

    # Assign the three managers
    objects = ActiveObjectsManager()  # DEFAULT: Only active objects
    all_objects = AllObjectsManager()  # All objects (active + deleted)
    deleted_objects = DeletedObjectsManager()  # Only deleted objects

    class Meta:
        abstract = True

    def delete(self, user=None, using=None, keep_parents=False):
        """
                Soft delete the object by setting deleted timestamp and user.

                Args:
                    user: User instance who is deleting the object (optional)
                    using: Database alias (optional)
                    keep_parents: Whether to keep parent objects in cascades (optional)
                """
        # ( date delete)
        # print("date", self.is_deleted)
        if self.is_deleted:
            raise ValueError("This object is already deleted")

        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user

        self.save(using=using, update_fields=['deleted_at', 'deleted_by'])

    def hard_delete(self, using=None, keep_parents=False):
        """
                Permanently delete the object from database.
                Calls the superclass delete() for actual removal.
                """
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """
                Restore a deleted object by clearing deleted fields.
                """
        if not self.is_deleted:
            raise ValueError("This object is not deleted")
        # print("From here restore function to be done")
        # print(self)
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['deleted_at', 'deleted_by'])

    @property
    def is_deleted(self):
        """
                Check if object is deleted.
                """
        # (date)
        print('self.is_deleted', self.deleted_at)
        print(self)
        return self.deleted_at is not None

    @property
    def is_active(self):
        """
                Check if object is active (not deleted).
                """
        return self.deleted_at is None

    def __str__(self):
        status = " (DELETED)" if self.is_deleted else ""
        return f"{super().__str__()}{status}"
