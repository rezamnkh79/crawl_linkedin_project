from django.conf import settings
from elasticsearch_dsl import Document, Text


class UserProfileDocument(Document):
    name = Text()
    studies = Text()
    field_of_work = Text()
    location = Text()
    profile_link = Text()

    class Index:
        name = 'user_profiles'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    def save(self, **kwargs):
        return super().save(**kwargs)
