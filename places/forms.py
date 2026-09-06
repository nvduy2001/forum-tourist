from django import forms

from .models import PlaceOwnershipRequest


class PlaceOwnershipRequestForm(forms.ModelForm):
    class Meta:
        model = PlaceOwnershipRequest
        fields = ['contact_name', 'contact_phone', 'contact_email', 'note']
