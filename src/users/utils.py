# In src/core/utils.py (or models.py)

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Override to include timestamp for expiration check
        return f"{user.pk}{timestamp}{user.is_active}"

    # Default timeout is 3 days; we use check_token's internal logic with a 1-day limit
    # Note: Django's generator uses settings.PASSWORD_RESET_TIMEOUT (default 3 days), but we can enforce in check
