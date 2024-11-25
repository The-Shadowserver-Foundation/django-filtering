from django.db import models


class Participant(models.Model):

    class SexChoices(models.TextChoices):
        UNKNOWN = "u", "Unknown"
        MALE = "m", "Male"
        FEMALE = "f", "Female"
        INTERSEX = "i", "Intersex"

    name = models.CharField(max_length=255)
    onboarded = models.DateTimeField()
    # FIXME Replace with birthdate and deathdate fields
    age = models.IntegerField()
    sex = models.CharField(max_length=1, choices=SexChoices, default=SexChoices.UNKNOWN)
    is_paid = models.BooleanField()
    payment_amount = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["id"]
