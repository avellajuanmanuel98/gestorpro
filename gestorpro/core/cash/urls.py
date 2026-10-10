from django.urls import path

from .views import (
    CurrentSessionView,
    RegisterListView,
    SessionCloseView,
    SessionDetailView,
    SessionListCreateView,
    SessionMovementView,
)

urlpatterns = [
    path('registers/', RegisterListView.as_view(), name='cash-registers'),
    path('sessions/', SessionListCreateView.as_view(), name='cash-sessions'),
    path('sessions/current/', CurrentSessionView.as_view(), name='cash-session-current'),
    path('sessions/<int:pk>/', SessionDetailView.as_view(), name='cash-session-detail'),
    path('sessions/<int:pk>/movements/', SessionMovementView.as_view(), name='cash-session-movements'),
    path('sessions/<int:pk>/close/', SessionCloseView.as_view(), name='cash-session-close'),
]
