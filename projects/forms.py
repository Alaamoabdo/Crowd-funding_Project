from django import forms
from django.core.exceptions import ValidationError

from .models import Comment, CommentReport, Donation, Project, ProjectReport, Rating, Tag


class ProjectForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        label='Tags',
        widget=forms.TextInput(attrs={'placeholder': 'Example: education, health, environment', 'class': 'tag-input'}),
        help_text='Enter tags separated by commas. You can add up to 8 tags.'
    )

    class Meta:
        model = Project
        fields = ('title', 'details', 'category', 'tags', 'target', 'start_time', 'end_time')
        labels = {
            'title': 'Title',
            'details': 'Details',
            'category': 'Category',
            'tags': 'Tags',
            'target': 'Target',
            'start_time': 'Start time',
            'end_time': 'End time',
        }
        widgets = {
            'details': forms.Textarea(attrs={'rows': 7}),
            'target': forms.NumberInput(attrs={'min': '1', 'step': '1'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_tags(self):
        raw_tags = self.cleaned_data.get('tags', '')
        names = []
        seen = set()
        for name in raw_tags.split(','):
            cleaned = name.strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered not in seen:
                seen.add(lowered)
                names.append(cleaned)
        if not names:
            raise forms.ValidationError('Enter at least one tag.')
        if len(names) > 8:
            raise forms.ValidationError('Choose up to 8 tags only.')
        return names

    def get_tag_objects(self):
        tag_names = self.cleaned_data.get('tags', [])
        objects = []
        for name in tag_names:
            tag = Tag.objects.filter(name__iexact=name).first()
            if tag is None:
                tag = Tag.objects.create(name=name)
            objects.append(tag)
        return objects

    @staticmethod
    def validate_uploaded_image(image):
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        extension = '.' + image.name.rsplit('.', 1)[-1].lower() if '.' in image.name else ''
        if extension not in allowed_extensions or not image.content_type.startswith('image/'):
            raise ValidationError('Upload JPG, PNG, or WEBP images only.')
        if image.size > 10 * 1024 * 1024:
            raise ValidationError('Each project image must be 10 MB or smaller.')


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ('amount',)
        labels = {'amount': 'Amount'}
        widgets = {'amount': forms.NumberInput(attrs={'min': '1', 'step': '0.01'})}

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Enter an amount greater than zero.')
        if self.project and amount > self.project.target - self.project.total_donations:
            raise forms.ValidationError('Donation cannot exceed the remaining project target.')
        return amount

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        labels = {'body': 'Comment'}
        widgets = {'body': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Share a thoughtful comment...'})}


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ('score',)
        labels = {'score': 'Rating'}
        widgets = {'score': forms.RadioSelect(choices=tuple((i, str(i)) for i in range(1, 6)))}


class ReportForm(forms.ModelForm):
    class Meta:
        model = ProjectReport
        fields = ('reason',)
        labels = {'reason': 'Reason'}
        widgets = {'reason': forms.Textarea(attrs={'rows': 4})}


class CommentReportForm(forms.ModelForm):
    class Meta:
        model = CommentReport
        fields = ('reason',)
        labels = {'reason': 'Reason'}
        widgets = {'reason': forms.Textarea(attrs={'rows': 3})}
