import base64
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            header, data = data.split(';base64,')
            extension = header.split('/')[-1]
            data = ContentFile(
                base64.b64decode(data),
                name=f'{uuid.uuid4()}.{extension}',
            )
        return super().to_internal_value(data)
