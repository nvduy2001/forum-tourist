from allauth.account.forms import SignupForm
from captcha.fields import CaptchaField
from django import forms

from .models import User


class CaptchaSignupForm(SignupForm):
    """Bảo mật: bắt buộc captcha khi đăng ký để chống bot/spam tài khoản."""

    captcha = CaptchaField()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'avatar', 'cover_image']
