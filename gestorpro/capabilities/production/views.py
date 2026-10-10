from decimal import Decimal, InvalidOperation

from rest_framework import filters, generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission

from . import services
from .models import ProductionBatch, Recipe
from .serializers import BatchSerializer, ProduceSerializer, RecipeInputSerializer, RecipeSerializer, can_see_costs


class RecipeListCreateView(generics.ListCreateAPIView):
    """Recetas ACTIVAS (una por producto). POST guarda (y versiona si hace falta)."""
    serializer_class = RecipeSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'recipes.view', 'POST': 'recipes.manage'}
    filter_backends = [filters.SearchFilter]
    search_fields = ['product__name', 'product__code']

    def get_queryset(self):
        return (Recipe.objects.filter(is_active=True).select_related('product__unit')
                .prefetch_related('lines__ingredient__unit', 'lines__unit'))

    def create(self, request, *args, **kwargs):
        data = RecipeInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        recipe = services.save_recipe(user=request.user, **data.validated_data)
        return Response(RecipeSerializer(recipe, context={'request': request}).data, status=status.HTTP_201_CREATED)


class RecipeDetailView(generics.RetrieveAPIView):
    serializer_class = RecipeSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'recipes.view'}

    def get_queryset(self):
        return Recipe.objects.select_related('product__unit')


class RecipePlanView(APIView):
    """GET /api/production/recipes/<id>/plan/?quantity=150 — ingredientes y costo para producir esa cantidad."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'production.register'}

    def get(self, request, pk):
        recipe = Recipe.objects.select_related('product__unit').filter(pk=pk, is_active=True).first()
        if recipe is None:
            raise ValidationError('Receta inexistente o inactiva.')
        try:
            qty = Decimal(request.query_params.get('quantity', recipe.yield_quantity))
        except InvalidOperation as exc:
            raise ValidationError({'quantity': 'Cantidad inválida.'}) from exc
        if qty <= 0:
            raise ValidationError({'quantity': 'La cantidad debe ser mayor que cero.'})
        show = can_see_costs({'request': request})
        rows, total = [], Decimal('0')
        for ing, needed in services.scaled_needs(recipe, qty):
            row = {'ingredient': ing.id, 'name': ing.name, 'unit_symbol': ing.unit.symbol, 'quantity': str(needed),
                   'stock': str(ing.stock), 'short': ing.stock < needed}
            if show:
                cost = services._q(needed * ing.avg_cost)
                total += cost
                row['cost'] = str(cost)
            rows.append(row)
        return Response({'recipe': recipe.id, 'quantity': str(qty), 'lines': rows,
                         'estimated_cost': str(services._q(total)) if show else None,
                         'estimated_unit_cost': str(services._q(total / qty)) if show else None})


class BatchListCreateView(generics.ListCreateAPIView):
    serializer_class = BatchSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'production.view', 'POST': 'production.register'}

    def get_queryset(self):
        qs = (ProductionBatch.objects.select_related('product__unit', 'recipe', 'created_by')
              .prefetch_related('consumptions__ingredient__unit'))
        if self.request.query_params.get('date'):
            qs = qs.filter(created_at__date=self.request.query_params['date'])
        return qs

    def create(self, request, *args, **kwargs):
        data = ProduceSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        batch = services.produce(user=request.user, **data.validated_data)
        return Response(BatchSerializer(batch, context={'request': request}).data, status=status.HTTP_201_CREATED)
