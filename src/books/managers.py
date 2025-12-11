from django.db import models
from django.db.models import ExpressionWrapper, Case, When, Value, Sum
from django.db.models.fields import BooleanField
from django.db.models.functions import Coalesce


class BookQuerySet(models.QuerySet):
    def can_sell(self):
        return self.prefetch_related('publisher', 'stock', 'stock__batches').annotate(
            total_quantity=Coalesce(Sum('stock__batches__remaining_quantity'), 0),
            can_sell=ExpressionWrapper(
                Case(
                    When(total_quantity__gt=0, stock__current_price__gt=0, then=Value(True)),
                    default=Value(False),
                ),
                output_field=BooleanField()
            )
        )


class BookManager(models.Manager):
    def get_queryset(self):
        return BookQuerySet(self.model, using=self._db)

    def can_sell(self):
        return self.get_queryset().can_sell()
