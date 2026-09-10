from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookViewSet,
    ChapterViewSet,
    RegisterView,
    SavedWordViewSet,
    TranslateViewSet,
)

router = DefaultRouter()

router.register(
    "books",
    BookViewSet,
    basename="book",
)
router.register(
    "chapters",
    ChapterViewSet,
    basename="chapter",
)
router.register(
    "words",
    SavedWordViewSet,
    basename="word",
)
router.register(
    "translate",
    TranslateViewSet,
    basename="translate",
)

urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
    path(
        "auth/register/",
        RegisterView.as_view(),
        name="register",
    ),
]