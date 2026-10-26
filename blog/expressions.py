from django.db.models import Func, IntegerField


class CharLength(Func):
    """Character length using the database LENGTH function."""

    function = "LENGTH"
    output_field = IntegerField()
