from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, CommentReportForm, DonationForm, ProjectForm, RatingForm, ReportForm
from .models import Category, Comment, CommentReport, Donation, Project, ProjectImage, ProjectReport, Rating


def home(request):
    active_projects = Project.objects.filter(
        status=Project.Status.ACTIVE,
    ).select_related('category').prefetch_related('tags', 'images').annotate(average_score=Avg('ratings__score'))
    query = request.GET.get('q', '').strip()
    search_results = active_projects
    if query:
        search_results = active_projects.filter(Q(title__icontains=query) | Q(tags__name__icontains=query)).distinct()

    return render(request, 'projects/home.html', {
        'top_rated_projects': active_projects.order_by('-average_score', '-created_at')[:5],
        'latest_projects': active_projects.order_by('-created_at')[:5],
        'featured_projects': active_projects.filter(featured=True).order_by('-created_at')[:5],
        'categories': Category.objects.all(),
        'search_results': search_results[:5] if query else None,
        'search_query': query,
    })


def project_list(request):
    projects = Project.objects.filter(status=Project.Status.ACTIVE).select_related('category', 'creator').prefetch_related('tags', 'images')
    return render(request, 'projects/project_list.html', {'projects': projects})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    projects = Project.objects.filter(category=category, status=Project.Status.ACTIVE).select_related('category').prefetch_related('tags', 'images')
    return render(request, 'projects/category_detail.html', {'category': category, 'projects': projects})


def category_list(request):
    return render(request, 'projects/category_list.html', {'categories': Category.objects.all()})


def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects
        .select_related('category', 'creator')
        .prefetch_related('tags', 'images', 'comments__author', 'ratings')
        .annotate(average_score=Avg('ratings__score')),
        pk=pk,
    )
    similar_projects = Project.objects.filter(status=Project.Status.ACTIVE, tags__in=project.tags.all()).exclude(pk=pk).distinct()[:4]
    context = {
        'project': project,
        'similar_projects': similar_projects,
        'donation_form': DonationForm(project=project),
        'comment_form': CommentForm(),
        'rating_form': RatingForm(instance=Rating(project=project, user=request.user)) if request.user.is_authenticated else RatingForm(),
        'report_form': ReportForm(),
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_create(request):
    form = ProjectForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        for image in request.FILES.getlist('images'):
            try:
                ProjectForm.validate_uploaded_image(image)
            except ValidationError as error:
                form.add_error(None, error)
        if form.errors:
            return render(request, 'projects/project_form.html', {'form': form})
        project = form.save(commit=False)
        project.creator = request.user
        project.save()
        project.tags.set(form.get_tag_objects())
        for position, image in enumerate(request.FILES.getlist('images')):
            ProjectImage.objects.create(project=project, image=image, position=position)
        messages.success(request, 'Your project campaign was created.')
        return redirect(project)
    return render(request, 'projects/project_form.html', {'form': form})


@login_required
def donate(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = DonationForm(request.POST or None, project=project)
    if request.method == 'POST' and form.is_valid():
        if project.status != Project.Status.ACTIVE:
            form.add_error(None, 'This campaign is not currently accepting donations.')
        else:
            donation = form.save(commit=False)
            donation.project = project
            donation.donor = request.user
            donation.save()
            messages.success(request, 'Thank you for supporting this project.')
            return redirect(project)
    return render(request, 'projects/project_detail.html', {'project': project, 'donation_form': form, 'comment_form': CommentForm(), 'rating_form': RatingForm(), 'report_form': ReportForm()})


@login_required
def add_comment(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = CommentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        comment = form.save(commit=False)
        comment.project = project
        comment.author = request.user
        comment.save()
        messages.success(request, 'Your comment was added.')
    return redirect(project)


@login_required
def add_reply(request, pk):
    parent = get_object_or_404(Comment, pk=pk, parent__isnull=True)
    form = CommentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        reply = form.save(commit=False)
        reply.project = parent.project
        reply.parent = parent
        reply.author = request.user
        reply.save()
        messages.success(request, 'Your reply was added.')
    return redirect(parent.project)


@login_required
def rate_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = RatingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        Rating.objects.update_or_create(project=project, user=request.user, defaults={'score': form.cleaned_data['score']})
        messages.success(request, 'Your rating was saved.')
    return redirect(project)


@login_required
def report_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ReportForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        report = form.save(commit=False)
        report.project = project
        report.reporter = request.user
        report.save()
        messages.success(request, 'Your report has been submitted successfully.', extra_tags='success')
        return redirect(project)
    return render(request, 'projects/report_form.html', {
        'form': form,
        'report_type': 'Project',
        'reported_object': project,
        'cancel_url': project.get_absolute_url(),
    })


@login_required
def report_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    form = CommentReportForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        report = form.save(commit=False)
        report.comment = comment
        report.reporter = request.user
        report.save()
        messages.success(request, 'Your report has been submitted successfully.', extra_tags='success')
        return redirect(comment.project)
    return render(request, 'projects/report_form.html', {
        'form': form,
        'report_type': 'Comment',
        'reported_object': comment,
        'cancel_url': comment.project.get_absolute_url(),
    })


@login_required
def cancel_project(request, pk):
    project = get_object_or_404(Project, pk=pk, creator=request.user)
    if request.method == 'POST':
        if project.total_donations < project.target * Decimal('0.25'):
            project.status = Project.Status.CANCELLED
            project.save(update_fields=('status',))
            messages.success(request, 'The project campaign was cancelled.')
        else:
            messages.success(request, 'This campaign remains active because it reached the 25% funding threshold.')
    return redirect(project)
