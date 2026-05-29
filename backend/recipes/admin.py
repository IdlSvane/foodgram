from django.contrib import admin

from recipes.models import (Ingredient, Recipe, RecipeIngredient, Tag,
                            UserRecipeRelation)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'favorites_count')
    list_filter = ('tags',)
    search_fields = ('name', 'author__username')
    inlines = (RecipeIngredientInline,)

    @admin.display(description='favorites')
    def favorites_count(self, obj):
        return obj.user_relations.filter(
            relation=UserRecipeRelation.FAVORITE
        ).count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(UserRecipeRelation)
class UserRecipeRelationAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'relation')
    list_filter = ('relation',)
    search_fields = ('user__email', 'user__username', 'recipe__name')
