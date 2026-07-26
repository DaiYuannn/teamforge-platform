from rest_framework import serializers

from .portal_models import PortalPublication, PortalSettings


class PortalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalSettings
        fields = (
            'team_name', 'tagline', 'summary', 'about_title', 'about_text',
            'logo_url', 'hero_image_url', 'story_image_url', 'contact_email',
            'join_title', 'join_message', 'join_url', 'updated_at',
        )
        read_only_fields = ('updated_at',)

    @staticmethod
    def _validate_public_url(value):
        if value and not value.startswith(('https://', 'http://', '/')):
            raise serializers.ValidationError('请输入 http(s) 地址或以 / 开头的站内地址')
        return value

    def validate_join_url(self, value):
        return self._validate_public_url(value)

    def validate_logo_url(self, value):
        return self._validate_public_url(value)

    def validate_hero_image_url(self, value):
        return self._validate_public_url(value)

    def validate_story_image_url(self, value):
        return self._validate_public_url(value)


class PortalPublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalPublication
        fields = (
            'content_type', 'object_id', 'is_public', 'is_featured',
            'member_consent', 'display_order', 'custom_title',
            'custom_summary', 'image_url', 'updated_at',
        )
        read_only_fields = ('content_type', 'object_id', 'member_consent', 'updated_at')

    def validate_is_public(self, value):
        publication = self.instance
        if (
            value
            and publication
            and publication.content_type == PortalPublication.ContentType.MEMBER
            and not publication.member_consent
        ):
            raise serializers.ValidationError('成员尚未授权公开个人资料')
        return value

    def validate_image_url(self, value):
        if value and not value.startswith(('https://', 'http://', '/')):
            raise serializers.ValidationError('请输入 http(s) 地址或以 / 开头的站内地址')
        return value


class PortalMemberConsentSerializer(serializers.Serializer):
    consent = serializers.BooleanField()
