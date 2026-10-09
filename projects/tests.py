from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Category, Comment, Donation, Project, ProjectImage, Rating, Tag


class ProjectFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='creator@example.com', password='A-secure-pass-123',
            first_name='Project', last_name='Creator', mobile_phone='01012345678',
        )
        self.backer = User.objects.create_user(
            email='backer@example.com', password='A-secure-pass-123',
            first_name='Project', last_name='Backer', mobile_phone='01112345678',
        )
        self.category = Category.objects.create(name='Technology')
        self.tag = Tag.objects.create(name='Community')
        self.project = Project.objects.create(
            creator=self.user, title='Community Solar', details='A useful project.',
            category=self.category, target=Decimal('1000'),
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(days=10),
        )
        self.project.tags.add(self.tag)

    def test_project_detail_shows_progress_and_rating(self):
        Rating.objects.create(project=self.project, user=self.backer, score=4)
        response = self.client.get(reverse('projects:detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Community Solar')
        self.assertContains(response, '4.0')

    def test_project_detail_shows_average_rating_across_all_ratings(self):
        Rating.objects.create(project=self.project, user=self.backer, score=2)
        Rating.objects.create(project=self.project, user=self.user, score=5)

        response = self.client.get(reverse('projects:detail', args=[self.project.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3.5')
        self.assertNotContains(response, '5.0')

    def test_authenticated_user_can_donate_and_rate(self):
        self.client.force_login(self.backer)
        donation_response = self.client.post(
            reverse('projects:donate', args=[self.project.pk]), {'amount': '100'}
        )
        rating_response = self.client.post(
            reverse('projects:rate', args=[self.project.pk]), {'score': '5'}
        )
        self.assertRedirects(donation_response, self.project.get_absolute_url())
        self.assertRedirects(rating_response, self.project.get_absolute_url())
        self.assertEqual(Donation.objects.get(project=self.project).amount, Decimal('100'))
        self.assertEqual(Rating.objects.get(project=self.project, user=self.backer).score, 5)

    def test_comment_uses_user_who_logged_in_after_an_existing_session(self):
        self.client.force_login(self.user)
        login_response = self.client.post(
            reverse('accounts:login'),
            {'username': self.backer.email, 'password': 'A-secure-pass-123'},
        )
        self.assertRedirects(login_response, reverse('projects:home'))

        comment_response = self.client.post(
            reverse('projects:comment', args=[self.project.pk]),
            {'body': 'A comment from the backer.'},
        )

        self.assertRedirects(comment_response, self.project.get_absolute_url())
        self.assertEqual(Comment.objects.get(project=self.project).author, self.backer)

    def test_authenticated_user_can_reply_to_a_top_level_comment(self):
        comment = Comment.objects.create(
            project=self.project,
            author=self.user,
            body='A question about the project.',
        )
        self.client.force_login(self.backer)

        response = self.client.post(
            reverse('projects:reply', args=[comment.pk]),
            {'body': 'Here is an answer.'},
        )

        self.assertRedirects(response, self.project.get_absolute_url())
        reply = Comment.objects.get(parent=comment)
        self.assertEqual(reply.author, self.backer)
        self.assertEqual(reply.project, self.project)
        self.assertContains(
            self.client.get(reverse('projects:detail', args=[self.project.pk])),
            'Here is an answer.',
        )

    def test_user_can_report_project_from_a_dedicated_page(self):
        self.client.force_login(self.backer)

        page_response = self.client.get(reverse('projects:report', args=[self.project.pk]))

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, 'Report Project')
        self.assertContains(page_response, self.project.title)
        self.assertContains(page_response, 'Submit Report')
        self.assertContains(page_response, 'Cancel')

        response = self.client.post(
            reverse('projects:report', args=[self.project.pk]),
            {'reason': 'The project details are misleading.'},
            follow=True,
        )

        report = self.project.reports.get()
        self.assertEqual(report.reporter, self.backer)
        self.assertEqual(report.reason, 'The project details are misleading.')
        self.assertRedirects(response, self.project.get_absolute_url())
        self.assertContains(response, 'Your report has been submitted successfully.')

    def test_user_can_report_comment_from_a_dedicated_page(self):
        comment = Comment.objects.create(
            project=self.project,
            author=self.user,
            body='This comment should be reviewed.',
        )
        self.client.force_login(self.backer)

        page_response = self.client.get(reverse('projects:report_comment', args=[comment.pk]))

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, 'Report Comment')
        self.assertContains(page_response, 'Project Creator')
        self.assertContains(page_response, comment.body)

        response = self.client.post(
            reverse('projects:report_comment', args=[comment.pk]),
            {'reason': 'This comment is abusive.'},
            follow=True,
        )

        report = comment.reports.get()
        self.assertEqual(report.reporter, self.backer)
        self.assertEqual(report.reason, 'This comment is abusive.')
        self.assertEqual(report.comment, comment)
        self.assertRedirects(response, self.project.get_absolute_url())
        self.assertContains(response, 'Your report has been submitted successfully.')

    def test_creator_can_cancel_below_25_percent_but_not_at_or_above_it(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('projects:cancel', args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertRedirects(response, self.project.get_absolute_url())
        self.assertEqual(self.project.status, Project.Status.CANCELLED)

        self.project.status = Project.Status.ACTIVE
        self.project.save(update_fields=('status',))
        Donation.objects.create(project=self.project, donor=self.backer, amount=Decimal('250'))
        self.client.post(reverse('projects:cancel', args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.ACTIVE)

    def test_homepage_lists_top_latest_featured_and_categories(self):
        for index in range(6):
            project = Project.objects.create(
                creator=self.user,
                title=f'Homepage project {index}',
                details='A homepage project.',
                category=self.category,
                target=Decimal('1000'),
                start_time=timezone.now() - timedelta(hours=1),
                end_time=timezone.now() + timedelta(days=10),
                featured=index < 2,
            )
            project.tags.add(self.tag)
            Rating.objects.create(project=project, user=self.backer, score=(index % 5) + 1)

        response = self.client.get(reverse('projects:home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['top_rated_projects']), 5)
        self.assertEqual(len(response.context['latest_projects']), 5)
        self.assertEqual(len(response.context['featured_projects']), 2)
        self.assertContains(response, 'Technology')

    def test_homepage_includes_active_project_with_rating_even_if_not_currently_live(self):
        future_project = Project.objects.create(
            creator=self.user,
            title='Queued campaign',
            details='Starts later but is active in the system.',
            category=self.category,
            target=Decimal('1000'),
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=20),
            featured=True,
        )
        future_project.tags.add(self.tag)
        Rating.objects.create(project=future_project, user=self.backer, score=5)

        response = self.client.get(reverse('projects:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(future_project, response.context['top_rated_projects'])
        self.assertIn(future_project, response.context['latest_projects'])
        self.assertIn(future_project, response.context['featured_projects'])

    def test_active_project_shows_donation_box_even_if_not_currently_live(self):
        future_project = Project.objects.create(
            creator=self.user,
            title='Future campaign',
            details='This campaign is active but not yet live by time.',
            category=self.category,
            target=Decimal('2000'),
            start_time=timezone.now() + timedelta(days=5),
            end_time=timezone.now() + timedelta(days=20),
        )
        future_project.tags.add(self.tag)

        self.client.force_login(self.backer)
        response = self.client.get(reverse('projects:detail', args=[future_project.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Support this project')
        self.assertContains(response, 'Donate now')

    def test_project_detail_has_image_slider_controls_when_images_exist(self):
        self.project.images.all().delete()
        ProjectImage.objects.create(project=self.project, image='project_images/a.png', position=0)
        ProjectImage.objects.create(project=self.project, image='project_images/b.png', position=1)
        ProjectImage.objects.create(project=self.project, image='project_images/c.png', position=2)

        response = self.client.get(reverse('projects:detail', args=[self.project.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-project-slider-prev')
        self.assertContains(response, 'data-project-slider-next')
        self.assertContains(response, 'data-image-counter')

    def test_homepage_search_finds_project_by_title_or_tag(self):
        response = self.client.get(reverse('projects:home'), {'q': 'Community'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Community Solar')

        response = self.client.get(reverse('projects:home'), {'q': 'Solar'})
        self.assertContains(response, 'Community Solar')

    def test_project_creation_page_accepts_multiple_tags(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('projects:create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tags')

        payload = {
            'title': 'Green City Initiative',
            'details': 'A sustainable urban project.',
            'category': self.category.pk,
            'tags': 'community, clean-energy, education',
            'target': '5000',
            'start_time': (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'end_time': (timezone.now() + timedelta(days=20)).strftime('%Y-%m-%dT%H:%M'),
        }
        response = self.client.post(reverse('projects:create'), payload)
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(title='Green City Initiative')
        self.assertEqual(project.tags.count(), 3)

    def test_project_creation_accepts_multiple_uploaded_images(self):
        self.client.force_login(self.user)
        payload = {
            'title': 'Multi image campaign',
            'details': 'This project should accept several uploaded images.',
            'category': self.category.pk,
            'tags': 'community',
            'target': '3000',
            'start_time': (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'end_time': (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%dT%H:%M'),
            'images': [
                SimpleUploadedFile('first.png', b'fake-image-data-1', content_type='image/png'),
                SimpleUploadedFile('second.png', b'fake-image-data-2', content_type='image/png'),
            ],
        }

        response = self.client.post(reverse('projects:create'), payload)
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(title='Multi image campaign')
        self.assertEqual(project.images.count(), 2)

    def test_category_page_shows_projects_in_category(self):
        response = self.client.get(reverse('projects:category', args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Community Solar')
