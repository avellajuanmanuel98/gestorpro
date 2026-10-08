from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from gestorpro.capabilities.hr.views import HRReportView
from gestorpro.platform.admin_panel.site import platform_admin_site

api = [
    # Core
    path('auth/', include('gestorpro.core.identity.urls')),
    path('tenant/', include('gestorpro.core.tenancy.urls')),
    path('customers/', include('gestorpro.core.customers.urls')),
    path('suppliers/', include('gestorpro.core.suppliers.urls')),
    path('catalog/', include('gestorpro.core.catalog.urls')),
    path('billing/', include('gestorpro.core.billing.urls')),
    path('reports/', include('gestorpro.core.reporting.urls')),
    # Capabilities
    path('employees/', include('gestorpro.capabilities.hr.urls')),
    path('reports/hr/', HRReportView.as_view(), name='report-hr'),
    path('assistant/', include('gestorpro.capabilities.assistant.urls')),
    # Documentación
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

urlpatterns = [
    path('admin/', platform_admin_site.urls),
    path('api/', include(api)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


def react_app(request, path=''):
    """Cualquier ruta que no sea API/admin/static sirve la SPA (React Router navega en cliente)."""
    index = settings.BASE_DIR / 'frontend' / 'dist' / 'index.html'
    if not index.exists():
        raise Http404('Frontend no compilado (npm run build).')
    return FileResponse(open(index, 'rb'), content_type='text/html')


urlpatterns += [re_path(r'^(?!api/|admin/|static/|media/).*$', react_app)]
