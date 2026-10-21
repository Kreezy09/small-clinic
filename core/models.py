"""Abstract model building blocks shared by the domain apps."""

from django.db import models


class TimestampedModel(models.Model):
    """Abstract model that records when a row was created and last updated."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
