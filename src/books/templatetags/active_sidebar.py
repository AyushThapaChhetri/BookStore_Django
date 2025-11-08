# templatetags/active_filters.py
from django import template

register = template.Library()

# Define your URL groups
URL_GROUPS = {
    'ecommerce': [
        'admin-book-list',
        'admin-stock-list',
        'admin_author_list',
        'admin_publisher_list',
        'admin_genre_list',
        'admin_order_list',
    ],
    'recycle_bin': [
        'book_recycle_bin',
        'book_restore',
        'book_permanent_delete'
    ],
    'dashboard': ['admin_dashboard'],
    'kanban': ['admin_kanban'],
    'inbox': ['admin_inbox'],
    'users': ['admin_users'],
    'books': ['admin_books']
}


@register.simple_tag
def active_class(request, target_url_name):
    """Return active Tailwind class if current URL matches target"""
    if request.resolver_match.url_name == target_url_name:
        return "bg-gray-100 dark:bg-gray-700"
    return ""


@register.simple_tag
def active_group_class(request, group_name):
    """Return active Tailwind class if current URL is in the specified group"""
    if group_name in URL_GROUPS and request.resolver_match.url_name in URL_GROUPS[group_name]:
        return "bg-none"
    return ""


@register.simple_tag
def dropdown_open(request, group_name):
    """Return 'block' if dropdown should be open, 'hidden' otherwise"""
    if group_name in URL_GROUPS and request.resolver_match.url_name in URL_GROUPS[group_name]:
        return "block"
    return "hidden"
