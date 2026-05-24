import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from CSV file.'

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            nargs='?',
            default='/app/data/ingredients.csv',
        )

    def handle(self, *args, **options):
        path = Path(options['path'])
        ingredients = []
        with path.open(encoding='utf-8') as file:
            reader = csv.reader(file)
            for name, measurement_unit in reader:
                ingredients.append(
                    Ingredient(name=name, measurement_unit=measurement_unit)
                )
        Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS('Ingredients loaded.'))
