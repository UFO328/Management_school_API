from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet,TeacherProfileViewSet
router = DefaultRouter()

router.register("teacher",TeacherViewSet,basename="teacher")
router.register("teacher-profile",TeacherProfileViewSet,basename="teacher-profile")

urlpatterns = router.urls 