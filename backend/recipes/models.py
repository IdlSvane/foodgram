from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from constants import (INGREDIENT_NAME_MAX_LENGTH, MEASUREMENT_UNIT_MAX_LENGTH,
                       MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT,
                       RECIPE_NAME_MAX_LENGTH, RELATION_MAX_LENGTH,
                       TAG_MAX_LENGTH)


class Tag(models.Model):
    name = models.CharField(
        'название',
        max_length=TAG_MAX_LENGTH,
        unique=True,
    )
    slug = models.SlugField(
        'слаг',
        max_length=TAG_MAX_LENGTH,
        unique=True,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'тег'
        verbose_name_plural = 'теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        'название',
        max_length=INGREDIENT_NAME_MAX_LENGTH,
    )
    measurement_unit = models.CharField(
        'единица измерения',
        max_length=MEASUREMENT_UNIT_MAX_LENGTH,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'ингредиент'
        verbose_name_plural = 'ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient_unit',
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='автор',
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    name = models.CharField('название', max_length=RECIPE_NAME_MAX_LENGTH)
    image = models.ImageField('изображение', upload_to='recipes/images/')
    text = models.TextField('описание')
    cooking_time = models.PositiveSmallIntegerField(
        'время приготовления',
        validators=(MinValueValidator(MIN_COOKING_TIME),)
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='теги',
        related_name='recipes',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='ингредиенты',
        through='RecipeIngredient',
        related_name='recipes',
    )
    pub_date = models.DateTimeField('дата публикации', auto_now_add=True)

    class Meta:
        ordering = ('-pub_date', 'id')
        verbose_name = 'рецепт'
        verbose_name_plural = 'рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='рецепт',
        on_delete=models.CASCADE,
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='ингредиент',
        on_delete=models.CASCADE,
    )
    amount = models.PositiveSmallIntegerField(
        'количество',
        validators=(MinValueValidator(MIN_INGREDIENT_AMOUNT),),
    )

    class Meta:
        default_related_name = 'recipe_ingredients'
        verbose_name = 'ингредиент в рецепте'
        verbose_name_plural = 'ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            )
        ]

    def __str__(self):
        return f'{self.ingredient} x {self.amount}'


class UserRecipeRelation(models.Model):
    FAVORITE = 'favorite'
    SHOPPING_CART = 'shopping_cart'
    RELATION_CHOICES = (
        (FAVORITE, 'избранное'),
        (SHOPPING_CART, 'список покупок'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='пользователь',
        on_delete=models.CASCADE,
        related_name='recipe_relations',
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='рецепт',
        on_delete=models.CASCADE,
        related_name='user_relations',
    )
    relation = models.CharField(
        'тип связи',
        max_length=RELATION_MAX_LENGTH,
        choices=RELATION_CHOICES,
    )

    class Meta:
        verbose_name = 'связь пользователя с рецептом'
        verbose_name_plural = 'связи пользователей с рецептами'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe', 'relation'),
                name='unique_user_recipe_relation',
            )
        ]

    def __str__(self):
        return f'{self.user} {self.relation} {self.recipe}'
