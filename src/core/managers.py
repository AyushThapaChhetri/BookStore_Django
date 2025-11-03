from django.db import models

from src.core.querysets import SafeDeleteQuerySet


class BaseSafeDeleteManager(models.Manager):
    """
        Base manager that contains ALL methods for SafeDelete functionality.
        Other managers inherit from this and just change the default get_queryset() behavior.
        It uses our custom QuerySet.
        """

    def get_queryset(self):
        """
                Base implementation - returns all objects using the custom QuerySet.
                Subclasses override this to filter by default.
                """
        return SafeDeleteQuerySet(self.model, using=self._db)


class ActiveObjectsManager(BaseSafeDeleteManager):
    """
        Manager that returns ONLY active (non-deleted) objects by default.
        Inherits all methods from BaseSafeDeleteManager.
        """

    def get_queryset(self):
        """
                Override to return only active objects by default.
                """
        return super().get_queryset().active()


class AllObjectsManager(BaseSafeDeleteManager):
    """
        Manager that returns ALL objects (active + deleted) by default.
        Inherits all methods from BaseSafeDeleteManager.
        """

    def get_queryset(self):
        """
                Override to return all objects by default (no filtering).
                """
        return super().get_queryset()


class DeletedObjectsManager(BaseSafeDeleteManager):
    """
        Manager that returns ONLY deleted objects by default.
        Inherits all methods from BaseSafeDeleteManager.
        """

    def get_queryset(self):
        """
                Return only deleted objects by default.
                """
        return super().get_queryset().deleted()

    def restore_all(self):
        """
                Restore all deleted objects.
                Calls the QuerySet's restore() method.
                """
        
        return self.queryset().restore()

    def hard_delete_all(self):
        """
                Permanently delete all deleted objects.
                Calls the QuerySet's hard_delete() method.
                """
        return self.queryset().hard_delete()
