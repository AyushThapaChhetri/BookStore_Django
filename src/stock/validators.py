from django.core.exceptions import ValidationError


def clean_price(self, price):
    if price is None:
        print("hello: ", price)
        return price
    # print("yoyo: ", price)
    if price < 0:
        raise ValidationError("Price must be non-negative.")
    return price


def clean_discount_percentage(self, discount_percentage):
    if discount_percentage is None:
        # print("hello: ", discount_percentage)
        return discount_percentage
    # print("yoyo: ", discount_percentage)

    if discount_percentage < 0 or discount_percentage > 100:
        raise ValidationError("Discount percentage must be between 0 and 100.")
    return discount_percentage
