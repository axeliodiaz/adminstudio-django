from rest_framework import serializers


class InstructorSerializer(serializers.Serializer):
    # Related user fields (used for creating/fetching the user)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)

    birthdate = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)

    # Instructor profile fields
    profile_image = serializers.ImageField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    tagline = serializers.CharField(required=False, allow_blank=True)

    # Social and contact
    website_url = serializers.URLField(required=False, allow_blank=True)
    instagram_username = serializers.CharField(required=False, allow_blank=True)
    tiktok_username = serializers.CharField(required=False, allow_blank=True)

    # Professional metadata
    is_verified = serializers.BooleanField(required=False)
    instructor_since = serializers.DateField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_blank=True)

    # Last playlist used per platform
    last_spotify_playlist = serializers.URLField(required=False, allow_blank=True)
    last_apple_music_playlist = serializers.URLField(required=False, allow_blank=True)
    last_youtube_music_playlist = serializers.URLField(required=False, allow_blank=True)
