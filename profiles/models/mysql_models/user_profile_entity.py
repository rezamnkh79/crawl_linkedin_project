from django.db import models


class UserProfile(models.Model):
    name = models.CharField(max_length=100)
    studies = models.CharField(max_length=100)
    field_of_work = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    profile_link = models.URLField()

    def __str__(self):
        return self.name
