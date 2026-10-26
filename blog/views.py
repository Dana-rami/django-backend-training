from django.http import HttpResponse, JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from .models import Post
from .serializers import PostSerializer
from .services import create_post


def home(request):
    return HttpResponse("Welcome to my Blog!")


async def status(request):
    """Return a small JSON status payload.

    This view does not touch the database or the post services.
    """
    return JsonResponse({"status": "ok"})


class PostPagination(PageNumberPagination):
    page_size = 2


class PostViewSet(ModelViewSet):
    queryset = Post.objects.all().order_by("id")
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PostPagination
    filter_backends = [SearchFilter]
    search_fields = ["title", "content"]

    def perform_create(self, serializer):
        serializer.instance = create_post(
            title=serializer.validated_data["title"],
            content=serializer.validated_data["content"],
            is_published=serializer.validated_data.get("is_published", False),
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        is_published = self.request.query_params.get("is_published")
        if is_published is None:
            return queryset
        if is_published.lower() == "true":
            return queryset.published()
        if is_published.lower() == "false":
            return queryset.unpublished()
        raise ValidationError(
            {"is_published": "Must be true or false."}
        )
