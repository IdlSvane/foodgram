from django.contrib import admin

from .models import Ingredient, Recipe, RecipeIngredient, Tag
from .models import UserRecipeRelation


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


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


admin.site.register(Tag)
admin.site.register(UserRecipeRelation)
