from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Panel de administración de Django
    path('admin/', admin.site.urls),

    # Documentación automática de la API (Swagger UI)
    # Entra a http://localhost:8000/api/docs/ para verla
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Rutas de cada app — cada una maneja sus propias URLs
    path('api/auth/', include('apps.users.urls')),
    path('api/clients/', include('apps.clients.urls')),
    path('api/billing/', include('apps.billing.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/companies/', include('apps.companies.urls')),
]

# En desarrollo, Django sirve los archivos de media (imágenes subidas)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all: cualquier ruta que no sea API ni admin sirve el index.html
# de React para que React Router maneje la navegación en el cliente.
def react_app(request, path=''):
    index = settings.BASE_DIR / 'frontend' / 'dist' / 'index.html'
    return FileResponse(open(index, 'rb'), content_type='text/html')

urlpatterns += [re_path(r'^(?!api/|admin/|static/).*$', react_app)]
