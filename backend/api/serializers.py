from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers

from api.fields import Base64ImageField
from constants import MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT
from recipes.models import (Ingredient, Recipe, RecipeIngredient, Tag,
                            UserRecipeRelation)
from users.models import Subscription

User = get_user_model()


class UserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = DjoserUserSerializer.Meta.fields + (
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(
                user=request.user,
                author=obj,
            ).exists()
        )

    def get_avatar(self, obj):
        request = self.context.get('request')
        if not obj.avatar:
            return None
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def to_representation(self, instance):
        request = self.context.get('request')
        url = instance.avatar.url if instance.avatar else None
        avatar = request.build_absolute_uri(url) if request and url else url
        return {'avatar': avatar}


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        request = self.context.get('request')
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        source='recipe_ingredients',
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_relation(self, obj, relation):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and UserRecipeRelation.objects.filter(
                user=request.user,
                recipe=obj,
                relation=relation,
            ).exists()
        )

    def get_is_favorited(self, obj):
        return self.get_relation(obj, UserRecipeRelation.FAVORITE)

    def get_is_in_shopping_cart(self, obj):
        return self.get_relation(obj, UserRecipeRelation.SHOPPING_CART)

    def get_image(self, obj):
        request = self.context.get('request')
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class RecipeIngredientWriteSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        min_value=MIN_INGREDIENT_AMOUNT,
        max_value=32767,
    )


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(
        min_value=MIN_COOKING_TIME,
        max_value=32767,
    )

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def validate(self, attrs):
        ingredients = attrs.get('ingredients')
        tags = attrs.get('tags')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': ['Добавьте ингредиенты.']}
            )
        if len({item['id'].id for item in ingredients}) != len(ingredients):
            raise serializers.ValidationError(
                {'ingredients': ['Ингредиенты не должны повторяться.']}
            )
        if not tags:
            raise serializers.ValidationError({'tags': ['Добавьте теги.']})
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError(
                {'tags': ['Теги не должны повторяться.']}
            )
        return attrs

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data

    def create_recipe_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount'],
            )
            for item in ingredients
        )

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data,
        )
        recipe.tags.set(tags)
        self.create_recipe_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.recipe_ingredients.all().delete()
        self.create_recipe_ingredients(instance, ingredients)
        return instance


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count')

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()
        limit = request.query_params.get('recipes_limit') if request else None
        if limit:
            try:
                recipes = recipes[: int(limit)]
            except ValueError:
                pass
        return RecipeMinifiedSerializer(
            recipes,
            many=True,
            context=self.context,
        ).data
