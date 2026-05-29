import base64
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from constants import DEFAULT_DEMO_DATA_PATH, DEMO_USER_PASSWORD
from recipes.models import (Ingredient, Recipe, RecipeIngredient, Tag,
                            UserRecipeRelation)
from users.models import Subscription

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo users, recipes and relations from JSON file.'

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            nargs='?',
            default=DEFAULT_DEMO_DATA_PATH,
        )

    def get_ingredient(self, name):
        ingredient = Ingredient.objects.filter(name__iexact=name).first()
        if ingredient:
            return ingredient
        return Ingredient.objects.create(name=name, measurement_unit='г')

    def get_image(self, recipe_data):
        return ContentFile(
            base64.b64decode(recipe_data['image']),
            name=f'{recipe_data["name"]}.png',
        )

    def load_data(self, path):
        with Path(path).open(encoding='utf-8') as file:
            return json.load(file)

    def create_users(self, users_data):
        users = {}
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data,
            )
            if created:
                password = user_data.get('password', DEMO_USER_PASSWORD)
                user.set_password(password)
                user.save()
            users[user.username] = user
        return users

    def create_recipes(self, recipes_data, users):
        tags = {tag.slug: tag for tag in Tag.objects.all()}
        recipes = {}
        for recipe_data in recipes_data:
            recipe, created = Recipe.objects.get_or_create(
                name=recipe_data['name'],
                author=users[recipe_data['author']],
                defaults={
                    'text': recipe_data['text'],
                    'cooking_time': recipe_data['cooking_time'],
                    'image': self.get_image(recipe_data),
                },
            )
            if created:
                recipe.tags.set(tags[slug] for slug in recipe_data['tags'])
                RecipeIngredient.objects.bulk_create(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=self.get_ingredient(item['name']),
                        amount=item['amount'],
                    )
                    for item in recipe_data['ingredients']
                )
            recipes[recipe_data['slug']] = recipe
        return recipes

    def create_subscriptions(self, subscriptions_data, users):
        for subscription_data in subscriptions_data:
            Subscription.objects.get_or_create(
                user=users[subscription_data['user']],
                author=users[subscription_data['author']],
            )

    def create_relations(self, relations_data, users, recipes):
        for relation_data in relations_data:
            UserRecipeRelation.objects.get_or_create(
                user=users[relation_data['user']],
                recipe=recipes[relation_data['recipe']],
                relation=relation_data['relation'],
            )

    @transaction.atomic
    def handle(self, *args, **options):
        data = self.load_data(options['path'])
        users = self.create_users(data['users'])
        recipes = self.create_recipes(data['recipes'], users)
        self.create_subscriptions(data.get('subscriptions', ()), users)
        self.create_relations(data.get('relations', ()), users, recipes)

        self.stdout.write(self.style.SUCCESS('Demo data loaded.'))
