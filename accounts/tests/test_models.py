from django.db import IntegrityError, transaction
from django.test import TestCase

from .factories import UserFactory


class CustomUserTests(TestCase):
    def test_email_must_be_unique(self):
        UserFactory(email='taken@example.com')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserFactory(email='taken@example.com')
