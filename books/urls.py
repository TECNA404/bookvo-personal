from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookViewSet,
    ChapterViewSet,
    RegisterView,
    SavedWordViewSet,
    TranslateView,
)

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("chapters", ChapterViewSet, basename="chapter")
router.register("words", SavedWordViewSet, basename="word")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "translate/",
        TranslateView.as_view(),
        name="translate",
    ),
    path(
        "auth/register/",
        RegisterView.as_view(),
        name="register",
    ),
]