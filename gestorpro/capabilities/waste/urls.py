from django.urls import path

from .views import ReasonListView, WasteListCreateView

urlpatterns = [
    path('', WasteListCreateView.as_view(), name='waste-list'),
    path('reasons/', ReasonListView.as_view(), name='waste-reasons'),
]
