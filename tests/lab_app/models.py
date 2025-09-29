from django.db import models


class Credential(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Staff(models.Model):
    name = models.CharField(max_length=255)
    credentials = models.ManyToManyField(Credential)

    def __str__(self):
        return f"{self.name} ({', '.join(self.credentials)}"

    class Meta:
        ordering = ["name"]


class Facility(models.Model):

    class OccupancySize(models.IntegerChoices):
        SMALL = 20
        MEDIUM = 40
        LARGE = 80

    name = models.CharField(max_length=255)
    max_occupancy = models.IntegerField(
        default=OccupancySize.SMALL,
        choices=OccupancySize.choices,
    )
    managed_by = models.ForeignKey(
        Staff,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        related_name='manager_of_facilities',
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-max_occupancy"]


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
    facility = models.ForeignKey(
        Facility,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='participants',
    )

    def __str__(self):
        return f"{self.name} @ {self.facility}"

    class Meta:
        ordering = ["id"]


class Study(models.Model):

    class State(models.IntegerChoices):
        DRAFT = 0, "Drafting"
        CANCEL = 10, "Cancelled"
        OPEN = 20, "Opened"
        REVIEW = 30, "Reviewing"
        CLOSE = 40, "Closed"

    name = models.CharField(max_length=255)
    country = models.CharField(max_length=3)  # ISO 3166-1 alpha-3
    state = models.IntegerField(choices=State, default=State.DRAFT)
    participants = models.ManyToManyField(Participant, blank=True)
