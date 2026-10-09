from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 2

        while True:
            existing = Tag.objects.filter(slug=slug).exclude(pk=self.pk).first()
            if not existing:
                self.slug = slug
                break
            slug = f'{base_slug}-{counter}'
            counter += 1

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=140)
    details = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='projects')
    tags = models.ManyToManyField(Tag, blank=True, related_name='projects')
    target = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def clean(self):
        if self.target <= 0:
            raise ValidationError({'target': 'The target must be greater than zero.'})
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'The end time must be after the start time.'})

    @property
    def total_donations(self):
        return self.donations.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    @property
    def progress_percent(self):
        if not self.target:
            return 0
        return min(100, int((self.total_donations / self.target) * 100))

    @property
    def average_rating(self):
        return self.ratings.aggregate(average=models.Avg('score'))['average'] or Decimal('0')

    @property
    def is_live(self):
        now = timezone.now()
        return self.status == self.Status.ACTIVE and self.start_time <= now <= self.end_time

    @property
    def can_cancel(self):
        return self.status == self.Status.ACTIVE and self.total_donations < self.target * Decimal('0.25')

    def get_absolute_url(self):
        return reverse('projects:detail', args=[self.pk])

    def __str__(self):
        return self.title


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='project_images/')
    caption = models.CharField(max_length=140, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('position', 'id')


class Donation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='donations')
    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def clean(self):
        if self.amount <= Decimal('0'):
            raise ValidationError({'amount': 'Donation must be greater than zero.'})


class Comment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)


class Rating(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_ratings')
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('project', 'user'), name='one_rating_per_user_project')]

    def clean(self):
        if self.score < 1 or self.score > 5:
            raise ValidationError({'score': 'Rating must be between 1 and 5.'})


class ProjectReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_reports')
    reason = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)


class CommentReport(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comment_reports')
    reason = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
