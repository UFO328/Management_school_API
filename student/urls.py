from rest_framework.routers import DefaultRouter
from .views import StudentViewSet,StudentProfileViewSet
router = DefaultRouter()

router.register("student",StudentViewSet,basename="student")
router.register("student-profile",StudentProfileViewSet,basename="student-profile")

urlpatterns = router.urls 