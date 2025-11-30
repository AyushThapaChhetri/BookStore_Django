from django.core.paginator import Paginator


def paginate_queryset(request, queryset, default_limit=10):
    # Get limit from GET params
    limit = request.GET.get('limit', default_limit)
    # print("limit before try", limit)
    try:
        limit = int(limit)
        # print("limit after try: ", limit)
    except (ValueError, TypeError):
        limit = default_limit

    # Get page number
    page_number = request.GET.get('page')

    # Create paginator
    paginator = Paginator(queryset, limit)
    page_obj = paginator.get_page(page_number)

    return page_obj, limit
