"""Thin authenticated HTTP views for engagement resources."""

from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.responses import success_response

from .models import Favorite, LearningProgress
from .serializers import FavoriteSerializer, LearningProgressSerializer
from .services import create_favorite, mark_story_complete, remove_favorite


class EngagementPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


def paginated_response(*, request, queryset, serializer_class, message):
    paginator = EngagementPagination()
    page = paginator.paginate_queryset(queryset, request)
    serialized = serializer_class(page, many=True)
    return success_response(
        data={
            "count": paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serialized.data,
        },
        message=message,
    )


class FavoriteDetailView(APIView):
    serializer_class = FavoriteSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, story_id):
        favorite = create_favorite(user=request.user, story_id=story_id)
        return success_response(
            data=FavoriteSerializer(favorite).data,
            message="Story added to favorites.",
            status_code=status.HTTP_201_CREATED,
        )

    def delete(self, request, story_id):
        remove_favorite(user=request.user, story_id=story_id)
        return success_response(message="Story removed from favorites.")


class FavoriteCollectionView(APIView):
    serializer_class = FavoriteSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = Favorite.objects.filter(user=request.user).select_related("story")
        return paginated_response(
            request=request,
            queryset=queryset,
            serializer_class=FavoriteSerializer,
            message="Favorites retrieved.",
        )


class ProgressDetailView(APIView):
    serializer_class = LearningProgressSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, story_id):
        progress = mark_story_complete(user=request.user, story_id=story_id)
        return success_response(
            data=LearningProgressSerializer(progress).data,
            message="Story marked complete.",
        )

    def get(self, request, story_id):
        progress = LearningProgress.objects.filter(
            user=request.user, story_id=story_id
        ).select_related("story").first()
        if progress is None:
            from django.http import Http404

            raise Http404
        return success_response(
            data=LearningProgressSerializer(progress).data,
            message="Learning progress retrieved.",
        )


class ProgressCollectionView(APIView):
    serializer_class = LearningProgressSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = LearningProgress.objects.filter(user=request.user).select_related("story")
        return paginated_response(
            request=request,
            queryset=queryset,
            serializer_class=LearningProgressSerializer,
            message="Learning progress retrieved.",
        )
