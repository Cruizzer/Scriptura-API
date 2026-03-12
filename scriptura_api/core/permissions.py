from rest_framework import permissions


class IsCollectionOwnerOrReadOnly(permissions.BasePermission):
    """Allow read access to everyone, but write access only to the collection owner."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Public collections are readable by anyone;
            # private collections are filtered in queryset to owner only.
            return True
        return request.user.is_authenticated and obj.user_id == request.user.id
