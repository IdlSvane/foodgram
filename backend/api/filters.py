from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag, UserRecipeRelation


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        queryset=Tag.objects.all(),
        to_field_name='slug',
    )
    is_favorited = filters.NumberFilter(method='filter_favorited')
    is_in_shopping_cart = filters.NumberFilter(method='filter_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

    def filter_relation(self, queryset, value, relation):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        if value:
            return queryset.filter(
                user_relations__user=user,
                user_relations__relation=relation,
            )
        return queryset.exclude(
            user_relations__user=user,
            user_relations__relation=relation,
        )

    def filter_favorited(self, queryset, name, value):
        return self.filter_relation(
            queryset,
            value,
            UserRecipeRelation.FAVORITE,
        )

    def filter_shopping_cart(self, queryset, name, value):
        return self.filter_relation(
            queryset,
            value,
            UserRecipeRelation.SHOPPING_CART,
        )
