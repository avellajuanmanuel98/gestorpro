from django.urls import path

from .views import (
    InvitationListCreateView,
    InvitationRevokeView,
    MemberDetailView,
    MemberListView,
    PermissionCatalogView,
    RoleDetailView,
    RoleListCreateView,
)

urlpatterns = [
    path('members/', MemberListView.as_view(), name='access-members'),
    path('members/<int:pk>/', MemberDetailView.as_view(), name='access-member-detail'),
    path('invitations/', InvitationListCreateView.as_view(), name='access-invitations'),
    path('invitations/<int:pk>/', InvitationRevokeView.as_view(), name='access-invitation-detail'),
    path('roles/', RoleListCreateView.as_view(), name='access-roles'),
    path('roles/<int:pk>/', RoleDetailView.as_view(), name='access-role-detail'),
    path('permissions/', PermissionCatalogView.as_view(), name='access-permissions'),
]
