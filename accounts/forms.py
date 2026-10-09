from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'mobile_phone', 'profile_picture')
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def clean_first_name(self):
        return self.clean_name('first_name')

    def clean_last_name(self):
        return self.clean_name('last_name')

    def clean_name(self, field_name):
        name = ' '.join(self.cleaned_data.get(field_name, '').split())
        if not name:
            raise forms.ValidationError('This field is required.')
        if not all(character.isalpha() or character in " -'" for character in name):
            raise forms.ValidationError('Use letters, spaces, hyphens, or apostrophes only.')
        return name

    def clean_mobile_phone(self):
        phone = self.cleaned_data['mobile_phone']
        if not phone.isdigit() or len(phone) != 11 or not phone.startswith(('010', '011', '012', '015')):
            raise forms.ValidationError('Enter a valid Egyptian mobile number.')
        return phone

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if not picture:
            return picture
            
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        extension = '.' + picture.name.rsplit('.', 1)[-1].lower() if '.' in picture.name else ''
        
        # التعديل هنا: الفحص يتم فقط إذا كانت صورة جديدة مرفوعة وبها content_type
        if hasattr(picture, 'content_type'):
            if extension not in allowed_extensions or not picture.content_type.startswith('image/'):
                raise forms.ValidationError('Upload a JPG, PNG, or WEBP image.')
        else:
            if extension not in allowed_extensions:
                raise forms.ValidationError('Upload a JPG, PNG, or WEBP image.')
                
        if hasattr(picture, 'size') and picture.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Profile picture must be 5 MB or smaller.')
            
        return picture


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'mobile_phone', 'profile_picture', 'birthdate', 'facebook_profile', 'country')
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_first_name(self):
        return RegistrationForm.clean_name(self, 'first_name')

    def clean_last_name(self):
        return RegistrationForm.clean_name(self, 'last_name')

    def clean_mobile_phone(self):
        return RegistrationForm.clean_mobile_phone(self)

    def clean_profile_picture(self):
        return RegistrationForm.clean_profile_picture(self)


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email')


class DeleteAccountForm(forms.Form):
    password = forms.CharField(label='Current password', widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user or not self.user.check_password(password):
            raise forms.ValidationError('The current password is incorrect.')
        return password