def applying_sorting(queryset, request, allowed_sorts, default='-created_at'):
    # Sorting helper
    sort = request.GET.get('sort')
    if sort in allowed_sorts:
        return queryset.order_by(allowed_sorts[sort])
    return queryset.order_by(default)


# Reusable allowed_sorts per model
ALLOWED_SORTS = {
    "book": {
        "name_asc": "title",
        "name_desc": "-title",
        "created_asc": "created_at",
        "created_desc": "-created_at",
    },
    "publisher": {
        "name_asc": "name",
        "name_desc": "-name",
        "created_asc": "created_at",
        "created_desc": "-created_at",
    },
    "author": {
        "name_asc": "name",
        "name_desc": "-name",
        "created_asc": "created_at",
        "created_desc": "-created_at",
    },

    "genre": {
        "name_asc": "name",
        "name_desc": "-name",
        "created_asc": "created_at",
        "created_desc": "-created_at",
    },
    # add more models here as needed

    "stock": {
        "price_asc": "price",
        "price_desc": "-price",
        "quantity_asc": "stock_quantity",
        "quantity_desc": "-stock_quantity",
        "available_first": "-is_available",  # available items first
        "unavailable_first": "is_available",  # unavailable items first
        "restock_asc": "last_restock_date",
        "restock_desc": "-last_restock_date",
        "created_asc": "created_at",
        "created_desc": "-created_at",
    },

}
