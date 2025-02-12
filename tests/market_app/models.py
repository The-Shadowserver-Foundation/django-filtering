from django.db import models


class Product(models.Model):

    class Category(models.TextChoices):
        BATH = 'Bath', 'Bath'
        KITCHEN = 'Kitchen', 'Kitchen'
        PATIO = 'Patio', 'Patio'

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, choices=Category)
    stocked = models.DateTimeField()
    brand = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["id"]
