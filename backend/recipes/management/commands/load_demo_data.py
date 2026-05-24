import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from recipes.models import UserRecipeRelation
from users.models import Subscription


User = get_user_model()

IMAGE = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD/'
    '//9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNo'
    'AAAAggCByxOyYQAAAABJRU5ErkJggg=='
)

USERS = (
    {
        'email': 'chef@example.com',
        'username': 'chef',
        'first_name': 'Иван',
        'last_name': 'Поваров',
    },
    {
        'email': 'baker@example.com',
        'username': 'baker',
        'first_name': 'Анна',
        'last_name': 'Пекарева',
    },
)

RECIPES = (
    {
        'author': 'chef',
        'name': 'Овощной салат',
        'text': 'Свежий салат для легкого завтрака.',
        'cooking_time': 10,
        'tags': ('breakfast',),
        'ingredients': (
            ('помидоры', 200),
            ('огурцы свежие', 150),
        ),
    },
    {
        'author': 'chef',
        'name': 'Домашний суп',
        'text': 'Простой горячий суп на каждый день.',
        'cooking_time': 40,
        'tags': ('lunch',),
        'ingredients': (
            ('картофель', 300),
            ('морковь', 100),
        ),
    },
    {
        'author': 'baker',
        'name': 'Быстрые блины',
        'text': 'Мягкие блины к ужину или завтраку.',
        'cooking_time': 25,
        'tags': ('breakfast', 'dinner'),
        'ingredients': (
            ('мука', 250),
            ('яйца куриные', 120),
        ),
    },
)


class Command(BaseCommand):
    help = 'Create demo users, recipes and relations.'

    def get_ingredient(self, name):
        ingredient = Ingredient.objects.filter(name__iexact=name).first()
        if ingredient:
            return ingredient
        return Ingredient.objects.create(name=name, measurement_unit='г')

    def get_image(self, recipe_name):
        return ContentFile(
            base64.b64decode(IMAGE),
            name=f'{recipe_name}.png',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for user_data in USERS:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data,
            )
            if created:
                user.set_password('foodgram123')
                user.save()
            users[user.username] = user

        tags = {tag.slug: tag for tag in Tag.objects.all()}

        recipes = []
        for recipe_data in RECIPES:
            recipe, created = Recipe.objects.get_or_create(
                name=recipe_data['name'],
                author=users[recipe_data['author']],
                defaults={
                    'text': recipe_data['text'],
                    'cooking_time': recipe_data['cooking_time'],
                    'image': self.get_image(recipe_data['name']),
                },
            )
            if created:
                recipe.tags.set(tags[slug] for slug in recipe_data['tags'])
                RecipeIngredient.objects.bulk_create(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=self.get_ingredient(name),
                        amount=amount,
                    )
                    for name, amount in recipe_data['ingredients']
                )
            recipes.append(recipe)

        Subscription.objects.get_or_create(
            user=users['baker'],
            author=users['chef'],
        )
        UserRecipeRelation.objects.get_or_create(
            user=users['baker'],
            recipe=recipes[0],
            relation=UserRecipeRelation.FAVORITE,
        )
        UserRecipeRelation.objects.get_or_create(
            user=users['baker'],
            recipe=recipes[1],
            relation=UserRecipeRelation.SHOPPING_CART,
        )

        self.stdout.write(self.style.SUCCESS('Demo data loaded.'))
