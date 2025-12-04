def applying_sorting(queryset, request=None, sort_by=None, allowed_sorts=None, default='-created_at'):
    # Sorting helper
    # sort = request.GET.get('sort')
    # print("hello")
    if allowed_sorts is None:
        allowed_sorts = {}

    # print('Sort got above: ', sort_by)

    # Prefer explicit sort_by, else fallback to request
    sort = sort_by or (request.GET.get("sort") if request else None)

    # print('Sort got: ', sort)

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
        "price_asc": "current_price",
        "price_desc": "-current_price",
        "quantity_asc": "total_quantity",
        "quantity_desc": "-total_quantity",
        "available_first": "-is_available",
        "unavailable_first": "is_available",
        "restock_asc": "last_restock_date",
        "restock_desc": "-last_restock_date",
        "created_asc": "created_at",
        "created_desc": "-created_at",
    },
    "order": {

        "created_asc": "created_at",
        "created_desc": "-created_at",

    },
    "bookstore": {
        "price_asc": "stock__current_price",
        "price_desc": "-stock__current_price",
        "quantity_asc": "total_quantity",
        "quantity_desc": "-total_quantity",
        "available_first": "-stock__is_available",
        "unavailable_first": "stock__is_available",
        "restock_asc": "stock__last_restock_date",
        "restock_desc": "-stock__last_restock_date",
        "created_asc": "created_at",
        "created_desc": "-created_at",
        "name_asc": "title",
        "name_desc": "-title",
    },

}
