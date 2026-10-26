from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.include_root_view = False
router.register("api/posts", views.PostViewSet, basename="post")

urlpatterns = [
    path("", views.home, name="blog-home"),
    path("api/status/", views.status, name="blog-status"),
    path("", include(router.urls)),
]
