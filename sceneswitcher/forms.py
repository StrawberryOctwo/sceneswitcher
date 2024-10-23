from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import UserProfile


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput
    )

    class Meta:
        model = UserProfile
        fields = ("email", "first_name", "last_name")

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

from django.core.mail import send_mail
from django.conf import settings
class ContactUsForm(forms.Form):
    first_name = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={
            'id': 'first-name',
            'name': 'first-name',
            'placeholder': 'First Name',
            'type': 'text',
            'style': 'color: black;',
        })
    )
    last_name = forms.CharField(max_length=100, 
            widget=forms.TextInput(attrs={
            'id': 'last-name',
            'name': 'last-name',
            'placeholder': 'Last Name',
            'type': 'text',
            'style': 'color: black;',
        }))
    email = forms.EmailField(
            widget=forms.TextInput(attrs={
            'id': 'email',
            'name': 'email',
            'placeholder': 'you@company.com',
            'type': 'email',
            'style': 'color: black;',
        }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'id': 'message',
    }))
    
    def send(self):
        message = f"first name: {self.cleaned_data['first_name']}\n"
        message += f"last name: {self.cleaned_data['last_name']}\n"
        message += f"email: {self.cleaned_data['email']}\n"
        message += f"message: {self.cleaned_data['message']}\n"
        
        return send_mail(
            "Contact Us Form Submission",
            message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
            )
