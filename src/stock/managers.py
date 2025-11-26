from django.db import models
from django.db.models import F, Prefetch, ExpressionWrapper, DecimalField, Subquery, OuterRef, IntegerField
from django.db.models import Sum, Value, Q
from django.db.models.functions import Coalesce, Cast, Abs


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

    def with_profit_loss(self, book_id):
        from src.stock.models import StockHistory, StockReservation

        DECIMAL = DecimalField(max_digits=14, decimal_places=2)

        sold_qty_sq = StockHistory.objects.filter(
            batch=OuterRef("pk"),
            change_type='sold',
            stock__book_id=book_id
        ).values("batch").annotate(

            total=Coalesce(
                Abs(Sum("quantity_change")),
                Value(0)
            )
        ).values("total")

        sold_order_ids_sq = StockHistory.objects.filter(
            batch=OuterRef(OuterRef("pk")),
            change_type='sold',
            stock__book_id=book_id,
            order__isnull=False
        ).values_list('order_id', flat=True)

        sold_amount_sq = StockReservation.objects.filter(
            batch=OuterRef("pk"),
            order_item__book_id=book_id,
            order_item__order_id__in=Subquery(sold_order_ids_sq),
            is_active=False
        ).annotate(

            line_total=ExpressionWrapper(
                Cast("reserved_quantity", DECIMAL) *
                (Cast("order_item__unit_price", DECIMAL) -
                 Coalesce(Cast("order_item__discount_amount", DECIMAL), Value(0, output_field=DECIMAL))),
                output_field=DECIMAL
            )
        ).values("batch").annotate(
            total=Coalesce(Sum("line_total"), Value(0, output_field=DECIMAL))
        ).values("total")

        return self.annotate(

            sold_qty=Coalesce(
                Subquery(sold_qty_sq, output_field=IntegerField()),
                Value(0)
            ),

            sold_amount=Coalesce(
                Subquery(sold_amount_sq, output_field=DECIMAL),
                Value(0, output_field=DECIMAL)
            ),
        ).annotate(

            cost_amount=ExpressionWrapper(
                Cast(F("sold_qty"), DECIMAL) * Cast("unit_cost", DECIMAL),
                output_field=DECIMAL
            ),

            net_amount=ExpressionWrapper(
                F("sold_amount") - F("cost_amount"),
                output_field=DECIMAL
            )
        )

    def with_full_details(self, book_id):
        return self.with_annotations().with_profit_loss(book_id)


class StockBatchManager(models.Manager):
    def get_queryset(self) -> StockBatchQuerySet:
        return StockBatchQuerySet(self.model, using=self._db)

    def with_annotations(self):
        return self.get_queryset().with_annotations()

    def with_profit_loss(self, book_id):
        return self.get_queryset().with_profit_loss(book_id)

    def with_full_details(self, book_id):
        return self.get_queryset().with_full_details(book_id)
