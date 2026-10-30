"""Fill the example database with sign-ins and samples, as often as it is run."""

from typing import Any

from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand

from partial_dates import PartialDate
from samples.models import Note, Sample

SIGN_INS = {
    "regular.user": {},
    "staff.user": {"is_staff": True},
    "super.user": {"is_staff": True, "is_superuser": True},
    "view-only.user": {"is_staff": True},
}
SAMPLES = [
    PartialDate(2024),
    PartialDate(2024, 3),
    PartialDate(2024, 3, 15),
    PartialDate(1850, 3),
    PartialDate(990),
]


class Command(BaseCommand):
    """Create the sign-ins and a sample at each precision, once each."""

    help = "Create the example sign-ins and samples."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create what is missing and leave what is there.

        Args:
            *args: Positional arguments of the command.
            **options: Options of the command.
        """
        permissions = Permission.objects.filter(
            content_type__app_label="samples",
            content_type__model__in=["sample", "note"],
        )
        view_permissions = permissions.filter(codename__startswith="view_")
        for username, flags in SIGN_INS.items():
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={"email": f"{username}@example.com", **flags},
            )
            user.set_password("password")
            user.save()
            if username == "staff.user":
                user.user_permissions.set(permissions)
            if username == "view-only.user":
                user.user_permissions.set(view_permissions)
        for collected in SAMPLES:
            Sample.objects.get_or_create(collected=collected)
        first = Sample.objects.get(collected=SAMPLES[0])
        Note.objects.get_or_create(sample=first, written=PartialDate(2024, 3))
        self.stdout.write("Seeded.")
