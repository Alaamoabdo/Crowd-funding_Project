from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import User
from .tokens import make_activation_token


class AccountFlowTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            'first_name': 'Mona',
            'last_name': 'Ali',
            'email': 'mona@example.com',
            'mobile_phone': '01012345678',
            'password1': 'A-secure-pass-123',
            'password2': 'A-secure-pass-123',
        }
        data.update(overrides)
        return data

    def test_registration_requires_valid_egyptian_phone(self):
        response = self.client.post(
            reverse('accounts:register'),
            self.registration_data(mobile_phone='02012345678'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertContains(response, 'valid Egyptian mobile number')

    def test_registration_validates_each_user_field(self):
        invalid_values = (
            ('first_name', ''),
            ('last_name', '123'),
            ('email', 'not-an-email'),
            ('mobile_phone', '010123'),
            ('password1', 'short'),
            ('password2', 'different-password-123'),
        )
        for field_name, value in invalid_values:
            with self.subTest(field_name=field_name):
                response = self.client.post(
                    reverse('accounts:register'),
                    self.registration_data(**{field_name: value}),
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(User.objects.exists())

        response = self.client.post(
            reverse('accounts:register'),
            self.registration_data(
                profile_picture=SimpleUploadedFile(
                    'profile.txt', b'not an image', content_type='text/plain'
                )
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_registration_sends_activation_and_blocks_login_until_activation(self):
        response = self.client.post(reverse('accounts:register'), self.registration_data())
        user = User.objects.get(email='mona@example.com')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(
            self.client.login(email=user.email, password='A-secure-pass-123')
        )

        token = make_activation_token(user)
        activation_response = self.client.get(
            reverse('accounts:activate', args=[token]), follow=True
        )
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertRedirects(activation_response, reverse('accounts:login'))
        self.assertTrue(self.client.login(email=user.email, password='A-secure-pass-123'))

    def test_invalid_activation_token_is_rejected(self):
        response = self.client.get(reverse('accounts:activate', args=['invalid-token']))
        self.assertEqual(response.status_code, 400)
        self.assertIn('invalid or has expired', response.content.decode())

    def test_profile_is_read_only_and_edit_profile_updates_allowed_fields(self):
        user = User.objects.create_user(
            email='profile@example.com', password='A-secure-pass-123',
            first_name='Old', last_name='Name', mobile_phone='01012345678',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'profile@example.com')
        self.assertContains(response, 'Edit Profile')
        self.assertNotContains(response, 'name="email"')
        self.assertNotContains(response, '<form')

        response = self.client.post(
            reverse('accounts:edit_profile'),
            {
                'first_name': 'New',
                'last_name': 'Name',
                'mobile_phone': '01112345678',
                'birthdate': '1995-04-12',
                'facebook_profile': 'https://facebook.com/profile',
                'country': 'Egypt',
            },
        )
        user.refresh_from_db()
        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertEqual(user.email, 'profile@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.mobile_phone, '01112345678')
        self.assertEqual(str(user.birthdate), '1995-04-12')
        self.assertEqual(user.facebook_profile, 'https://facebook.com/profile')
        self.assertEqual(user.country, 'Egypt')

        profile_response = self.client.get(reverse('accounts:profile'))
        self.assertContains(profile_response, '12 Apr, 1995')
        self.assertContains(profile_response, 'View profile')
        self.assertContains(profile_response, 'Egypt')

    def test_profile_update_validates_mobile_phone(self):
        user = User.objects.create_user(
            email='profile-invalid@example.com', password='A-secure-pass-123',
            first_name='Profile', last_name='User', mobile_phone='01012345678',
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse('accounts:edit_profile'),
            {
                'first_name': 'Profile',
                'last_name': 'User',
                'mobile_phone': '123',
            },
        )
        user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.mobile_phone, '01012345678')
        self.assertContains(response, 'valid Egyptian mobile number')

    def test_login_redirects_home_and_profile_has_no_quick_links(self):
        user = User.objects.create_user(
            email='homeflow@example.com', password='A-secure-pass-123',
            first_name='Home', last_name='Flow', mobile_phone='01012345678',
            is_active=True,
        )

        response = self.client.post(
            reverse('accounts:login'),
            {'username': user.email, 'password': 'A-secure-pass-123'},
            follow=True,
        )
        self.assertRedirects(response, reverse('projects:home'))

        self.client.force_login(user)
        profile_response = self.client.get(reverse('accounts:profile'))
        self.assertNotContains(profile_response, 'View profile')
        self.assertNotContains(profile_response, 'View projects')
        self.assertNotContains(profile_response, 'View donations')

    def test_account_deletion_requires_confirmation(self):
        user = User.objects.create_user(
            email='delete@example.com', password='A-secure-pass-123',
            first_name='Delete', last_name='Me', mobile_phone='01012345678',
        )
        self.client.force_login(user)
        response = self.client.post(reverse('accounts:delete_account'), {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertContains(response, 'Current password')

        response = self.client.post(
            reverse('accounts:delete_account'),
            {'confirm': 'yes', 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertContains(response, 'current password is incorrect')

        response = self.client.post(
            reverse('accounts:delete_account'),
            {'confirm': 'yes', 'password': 'A-secure-pass-123'},
        )
        self.assertRedirects(response, reverse('projects:home'))
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
