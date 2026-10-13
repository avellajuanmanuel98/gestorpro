from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.utils.csp import CSP
from django.views.decorators.csp import csp_override
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from gestorpro.capabilities.hr.views import HRReportView
from gestorpro.platform.admin_panel.site import platform_admin_site

api = [
    # Core
    path('auth/', include('gestorpro.core.identity.urls')),
    path('platform/', include('gestorpro.platform.console.urls')),
    path('tenant/', include('gestorpro.core.tenancy.urls')),
    path('access/', include('gestorpro.core.access.urls')),
    path('audit/', include('gestorpro.core.audit.urls')),
    path('customers/', include('gestorpro.core.customers.urls')),
    path('suppliers/', include('gestorpro.core.suppliers.urls')),
    path('catalog/', include('gestorpro.core.catalog.urls')),
    path('billing/', include('gestorpro.core.billing.urls')),
    path('sales/', include('gestorpro.core.sales.urls')),
    path('cash/', include('gestorpro.core.cash.urls')),
    path('inventory/', include('gestorpro.core.inventory.urls')),
    path('purchases/', include('gestorpro.core.purchasing.urls')),
    path('analytics/', include('gestorpro.core.analytics.urls')),
    path('reports/', include('gestorpro.core.reporting.urls')),
    # Capabilities
    path('employees/', include('gestorpro.capabilities.hr.urls')),
    path('reports/hr/', HRReportView.as_view(), name='report-hr'),
    path('assistant/', include('gestorpro.capabilities.assistant.urls')),
    path('production/', include('gestorpro.capabilities.production.urls')),
    path('waste/', include('gestorpro.capabilities.waste.urls')),
    # Verticals
    path('bakery/', include('gestorpro.verticals.bakery.urls')),
]

# Documentación de la API: en desarrollo, o si se habilita a propósito. En producción no se
# publica el mapa completo de la API. Swagger UI carga sus archivos desde jsDelivr: solo esa
# página amplía la CSP para ese origen.
if settings.DEBUG or getattr(settings, 'API_DOCS_ENABLED', False):
    _docs_csp = {**settings.SECURE_CSP, 'script-src': [CSP.SELF, 'https://cdn.jsdelivr.net', CSP.UNSAFE_INLINE],
                 'style-src': [CSP.SELF, 'https://cdn.jsdelivr.net', CSP.UNSAFE_INLINE],
                 'img-src': [CSP.SELF, 'data:', 'https://cdn.jsdelivr.net']}
    api += [
        path('schema/', SpectacularAPIView.as_view(), name='schema'),
        path('docs/', csp_override(_docs_csp)(SpectacularSwaggerView.as_view(url_name='schema')), name='swagger-ui'),
    ]

urlpatterns = [
    path('admin/', platform_admin_site.urls),
    path('api/', include(api)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, 'SERVE_MEDIA', False):
    # Edición local: no hay servidor web aparte para las imágenes subidas
    urlpatterns += [re_path(rf"^{settings.MEDIA_URL.strip('/')}/(?P<path>.*)$", serve,
                            {'document_root': settings.MEDIA_ROOT})]


def react_app(request, path=''):
    """Cualquier ruta que no sea API/admin/static sirve la SPA (React Router navega en cliente)."""
    index = settings.BASE_DIR / 'frontend' / 'dist' / 'index.html'
    if not index.exists():
        raise Http404('Frontend no compilado (npm run build).')
    return FileResponse(open(index, 'rb'), content_type='text/html')


urlpatterns += [re_path(r'^(?!api/|admin/|static/|media/).*$', react_app)]
