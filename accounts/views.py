from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from smtplib import SMTPException
from django.core import signing
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import DeleteAccountForm, EmailAuthenticationForm, ProfileForm, RegistrationForm
from .models import User
from .tokens import make_activation_token, read_activation_token


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = RegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        token = make_activation_token(user)
        activation_url = request.build_absolute_uri(reverse('accounts:activate', args=[token]))
        try:
            send_mail(
                'Activate your Crowdfunding account',
                f'Activate your account within 24 hours: {activation_url}',
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@crowdfunding.local'),
                [user.email],
            )
        except (OSError, SMTPException, ValueError):
            user.delete()
            form.add_error(None, 'We could not send the activation email. Check the email server settings and try again.')
            return render(request, 'accounts/register.html', {'form': form})
        return render(request, 'accounts/registration_sent.html', {'email': user.email})
    return render(request, 'accounts/register.html', {'form': form})


def activate(request, token):
    try:
        data = read_activation_token(token)
    except (signing.BadSignature, signing.SignatureExpired):
        return render(request, 'accounts/activation_invalid.html', status=400)
    user = get_object_or_404(User, pk=data['user_id'], email=data['email'])
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])
    messages.success(request, 'Your account is active. You can now log in.')
    return redirect('accounts:login')


def login_view(request):
    if request.user.is_authenticated and request.method != 'POST':
        return redirect('projects:home')
    form = EmailAuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next') or 'projects:home')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def dashboard(request):
    return render(request, 'accounts/dashboard.html')


@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {
        'my_projects': request.user.projects.all(),
        'my_donations': request.user.donations.select_related('project').all(),
    })


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile was updated successfully.')
        return redirect('accounts:profile')
    return render(request, 'accounts/edit_profile.html', {
        'form': form,
    })


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None, user=request.user)
    if request.method == 'POST' and request.POST.get('confirm') == 'yes' and form.is_valid():
        request.user.delete()
        logout(request)
        messages.success(request, 'Your account was deleted.')
        return redirect('projects:home')
    return render(request, 'accounts/delete_account.html', {'form': form})
