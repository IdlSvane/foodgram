from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from recipes.models import UserRecipeRelation
from users.models import Subscription

from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import AvatarSerializer, IngredientSerializer
from .serializers import PasswordSerializer, RecipeMinifiedSerializer
from .serializers import RecipeReadSerializer, RecipeWriteSerializer
from .serializers import SubscriptionSerializer, TagSerializer
from .serializers import TokenCreateSerializer, UserCreateSerializer
from .serializers import UserSerializer, get_token_for_user


User = get_user_model()


class UserViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                  mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all().order_by('id')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('subscriptions', 'subscribe'):
            return SubscriptionSerializer
        if self.action == 'avatar':
            return AvatarSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def me(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('post',),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def set_password(self, request):
        serializer = PasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('post',),
        permission_classes=(permissions.AllowAny,),
    )
    def reset_password(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('put', 'delete'),
        url_path='me/avatar',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def avatar(self, request):
        if request.method == 'DELETE':
            request.user.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscriptions(self, request):
        authors = User.objects.filter(subscribers__user=request.user)
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page,
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()
        if request.method == 'DELETE':
            deleted, _ = Subscription.objects.filter(
                user=request.user,
                author=author,
            ).delete()
            if not deleted:
                return Response(
                    {'errors': 'Вы не подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        if author == request.user:
            return Response(
                {'errors': 'Нельзя подписаться на себя.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            author=author,
        )
        if not created:
            return Response(
                {'errors': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = SubscriptionSerializer(
            subscription.author,
            context={'request': request},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags',
        'recipe_ingredients__ingredient',
    )
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_permissions(self):
        if self.action in (
            'create',
            'update',
            'partial_update',
            'destroy',
            'favorite',
            'shopping_cart',
            'download_shopping_cart',
        ):
            return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]
        return [permission() for permission in self.permission_classes]

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def create_relation(self, request, pk, relation):
        recipe = get_object_or_404(Recipe, pk=pk)
        _, created = UserRecipeRelation.objects.get_or_create(
            user=request.user,
            recipe=recipe,
            relation=relation,
        )
        if not created:
            return Response(
                {'errors': 'Рецепт уже добавлен.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RecipeMinifiedSerializer(
            recipe,
            context={'request': request},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_relation(self, request, pk, relation):
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = UserRecipeRelation.objects.filter(
            user=request.user,
            recipe=recipe,
            relation=relation,
        ).delete()
        if not deleted:
            return Response(
                {'errors': 'Рецепта нет в списке.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=('post', 'delete'))
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.create_relation(
                request,
                pk,
                UserRecipeRelation.FAVORITE,
            )
        return self.delete_relation(request, pk, UserRecipeRelation.FAVORITE)

    @action(detail=True, methods=('post', 'delete'))
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.create_relation(
                request,
                pk,
                UserRecipeRelation.SHOPPING_CART,
            )
        return self.delete_relation(
            request,
            pk,
            UserRecipeRelation.SHOPPING_CART,
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__user_relations__user=request.user,
            recipe__user_relations__relation=UserRecipeRelation.SHOPPING_CART,
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit',
        ).annotate(total=Sum('amount')).order_by('ingredient__name')

        lines = ['Список покупок Foodgram', '']
        lines.extend(
            (
                f'{item["ingredient__name"]} '
                f'({item["ingredient__measurement_unit"]}) - '
                f'{item["total"]}'
            )
            for item in ingredients
        )
        response = HttpResponse(
            '\n'.join(lines),
            content_type='text/plain; charset=utf-8',
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping-list.txt"'
        )
        return response

    @action(detail=True, methods=('get',), url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        path = reverse('recipe-detail', kwargs={'pk': recipe.pk})
        return Response({'short-link': request.build_absolute_uri(path)})


class TokenLoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = TokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = get_token_for_user(serializer.validated_data['user'])
        return Response({'auth_token': token})


class TokenLogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
