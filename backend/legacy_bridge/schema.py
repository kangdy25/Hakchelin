from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SupabaseJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "legacy_bridge.authentication.SupabaseJWTAuthentication"
    name = "SupabaseJWT"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
