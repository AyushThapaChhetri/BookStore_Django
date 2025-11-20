from django.db import models
from django.db.models import Prefetch
from django.db.models import Sum, Value, Q
from django.db.models.functions import Coalesce


class StockBatchQuerySet(models.QuerySet):
    def with_annotations(self):
        from src.stock.models import StockReservation

        return self.annotate(
            restock_total=Coalesce(
                Sum('history__quantity_change', filter=Q(history__change_type='restock')),
                Value(0)
            ),
            edit_total=Coalesce(
                Sum('history__quantity_change', filter=Q(history__change_type='editstock')),
                Value(0)
            ),
            sold_total=Coalesce(
                Sum('history__quantity_change', filter=Q(history__change_type='sold')),
                Value(0)
            ),
        ).select_related('supplier').prefetch_related(
            'history',
            'history__order',
            'history__order__items',
            Prefetch(
                'reservations',
                queryset=StockReservation.objects.filter(is_active=False)
                .select_related('order_item__order')
            )
        )


class StockBatchManager(models.Manager):
    def get_queryset(self) -> StockBatchQuerySet:
        return StockBatchQuerySet(self.model, using=self._db)

    def with_annotations(self):
        return self.get_queryset().with_annotations()
