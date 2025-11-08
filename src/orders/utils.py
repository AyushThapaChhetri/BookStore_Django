from django.db.models import Q


def search_order(queryset, query=None):
    if query:
        return queryset.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(uuid__icontains=query)
        )

    return queryset
