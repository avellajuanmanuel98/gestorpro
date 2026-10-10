from django.urls import path

from .views import ReasonListView, WasteListCreateView, WasteSummaryView

urlpatterns = [
    path('', WasteListCreateView.as_view(), name='waste-list'),
    path('reasons/', ReasonListView.as_view(), name='waste-reasons'),
    path('summary/', WasteSummaryView.as_view(), name='waste-summary'),
]
