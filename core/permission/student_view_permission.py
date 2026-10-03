from rest_framework.permissions import DjangoModelPermissions


class SchoolModelPermissions(DjangoModelPermissions):

    
    def get_required_permissions(self, method, model_cls):
        if method in ["GET","HEAD","OPTIONS"]:
            return [f"{model_cls._meta.app_label}.view_{model_cls._meta.model_name}"]

        if method == "POST":
            return [f"{model_cls._meta.app_label}.add_{model_cls._meta.model_name}"]

        if method in ["PUT", "PATCH"]:
            return [f"{model_cls._meta.app_label}.change_{model_cls._meta.model_name}"]

        if method == "DELETE":
            return [f"{model_cls._meta.app_label}.delete_{model_cls._meta.model_name}"]

        return []