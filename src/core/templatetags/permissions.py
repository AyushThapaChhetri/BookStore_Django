from django import template

register = template.Library()


@register.filter(name='has_perm')
def has_perm(user, perm_name):
    return user.has_perm(perm_name)
