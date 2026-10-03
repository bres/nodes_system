from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Compatibility wrapper for django-watson's buildwatson command"

    def add_arguments(self, parser):
        parser.add_argument("apps", nargs="*", action="store", default=[])
        parser.add_argument("--engine", action="store", default=None)
        parser.add_argument("--slim", action="store_true", default=False)
        parser.add_argument("--non-atomic", action="store_true", default=False)
        parser.add_argument("--batch-size", action="store", default=100, type=int)

    def handle(self, *args, **options):
        command_args = list(options.get("apps", []))
        command_kwargs = {
            "verbosity": options.get("verbosity", 1),
            "engine": options.get("engine"),
            "slim": options.get("slim"),
            "non_atomic": options.get("non_atomic"),
            "batch_size": options.get("batch_size"),
        }
        call_command("buildwatson", *command_args, **command_kwargs)
