# In src/core/utils.py (or models.py)

import io
import os
import uuid

from PIL import Image
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Override to include timestamp for expiration check
        return f"{user.pk}{timestamp}{user.is_active}"

    # Default timeout is 3 days; we use check_token's internal logic with a 1-day limit
    # Note: Django's generator uses settings.PASSWORD_RESET_TIMEOUT (default 3 days), but we can enforce in check


def compress_image(image, quality=70):
    img = Image.open(image)

    # print('lllll')

    if img.mode in ("RGBA", "P"):
        # print('jjjjj')
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", optimize=True, quality=quality)
    buffer.seek(0)
    # print('kkkkk')
    new_name = f"compressed_{uuid.uuid4()}.jpg"
    # print('nnnn:  ', new_name)
    return ContentFile(buffer.read(), new_name)


def validate_and_compress_image(image, max_size=2 * 1024 * 1024, compress=True):
    if not image:
        print('no image: ', image)
        return None
    # print('kkkkkkk: ', image)
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError("Only JPG, JPEG, PNG, GIF, and WEBP images are allowed.")

    valid_mime_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
        raise ValidationError("Invalid image file type.")

    if image.size > max_size:
        raise ValidationError(f"Image too large (max {max_size // (1024 * 1024)}MB).")

    if compress:
        # print('cccccc')
        return compress_image(image)

    return image
