from django.contrib import admin

from .models import Stock, StockBatch, StockHistory, PriceHistory, StockReservation


class StockBatchInline(admin.TabularInline):
    model = StockBatch
    extra = 1
    fields = ('received_date', 'initial_quantity', 'unit_cost', 'supplier', 'notes')
    readonly_fields = ('remaining_quantity',)


class StockHistoryInline(admin.TabularInline):
    model = StockHistory
    extra = 0  # No manual add
    readonly_fields = ('change_type', 'quantity_change', 'before_quantity', 'after_quantity', 'reason', 'changed_by',
                       'order', 'created_at')
    can_delete = False


class PriceHistoryInline(admin.TabularInline):
    model = PriceHistory
    extra = 0
    readonly_fields = ('old_price', 'new_price', 'old_discount_percentage', 'new_discount_percentage', 'changed_by',
                       'reason', 'created_at')
    can_delete = False


class StockReservationInline(admin.TabularInline):
    model = StockReservation
    extra = 0
    readonly_fields = ('order_item', 'batch', 'reserved_quantity', 'is_active')
    can_delete = False


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('book', 'current_price', 'current_discount_percentage', 'total_remaining_quantity', 'is_available',
                    'last_restock_date')
    list_filter = ('is_available',)
    search_fields = ('book__title',)
    readonly_fields = ('total_remaining_quantity', 'is_available', 'last_restock_date')
    fields = ('book', 'current_price', 'current_discount_percentage')
    inlines = [StockBatchInline, StockHistoryInline, PriceHistoryInline, StockReservationInline]


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ('stock', 'change_type', 'quantity_change', 'changed_by', 'created_at')
    list_filter = ('change_type',)
    readonly_fields = ('stock', 'batch', 'change_type', 'quantity_change', 'before_quantity', 'after_quantity',
                       'reason', 'changed_by', 'order', 'created_at')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('stock', 'old_price', 'new_price', 'changed_by', 'created_at')
    readonly_fields = ('stock', 'old_price', 'new_price', 'old_discount_percentage', 'new_discount_percentage',
                       'changed_by', 'reason', 'created_at')


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ('order_item', 'batch', 'reserved_quantity', 'is_active')
    list_filter = ('is_active',)
    readonly_fields = ('order_item', 'batch', 'reserved_quantity', 'is_active')
