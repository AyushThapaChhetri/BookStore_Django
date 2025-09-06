from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_initial_roles(sender, **kwargs):
    from django.contrib.auth.models import Group
    from django.contrib.auth import get_user_model
    from decouple import config

    print("[post_migrate] Running create_initial_roles...")

    group_names = ["super_admin", "employee", "client"]
    for name in group_names:
        Group.objects.get_or_create(name=name)
        print(f"Group '{name}' ensured.")

    User = get_user_model()
    email = config("DJANGO_SUPERUSER_EMAIL")
    password = config("DJANGO_SUPERUSER_PASSWORD")

    if not User.objects.filter(email=email).exists():
        user = User.objects.create_superuser(email=email, password=password)
        print(f"Superuser '{email}' created.")

        super_admin_group = Group.objects.get(name="super_admin")
        user.groups.add(super_admin_group)
        print(f"Superuser '{email}' added to 'super admin' group.")
    else:
        print(f"Superuser '{email}' already exists.")


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.users'

    def ready(self):
        post_migrate.connect(create_initial_roles, sender=self)
