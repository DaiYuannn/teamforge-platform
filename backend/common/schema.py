"""drf-spectacular extensions for shared API infrastructure."""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


class ScopedJWTAuthenticationScheme(SimpleJWTScheme):
    """Describe the project-specific JWT authenticator as HTTP Bearer auth."""

    target_class = 'common.authentication.ScopedJWTAuthentication'
    name = 'bearerAuth'


def success_response_schema(name, data):
    """Build the API's standard success envelope around a response serializer."""

    return inline_serializer(
        name=name,
        fields={
            'code': serializers.IntegerField(default=0),
            'message': serializers.CharField(),
            'data': data,
        },
    )
