from django.core.management.base import BaseCommand

from recipes.models import Tag

TAGS = (
    ('Завтрак', 'breakfast'),
    ('Обед', 'lunch'),
    ('Ужин', 'dinner'),
)


class Command(BaseCommand):
    help = 'Create default Foodgram tags.'

    def handle(self, *args, **options):
        for name, slug in TAGS:
            Tag.objects.get_or_create(name=name, slug=slug)
        self.stdout.write(self.style.SUCCESS('Tags loaded.'))
