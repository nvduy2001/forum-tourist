from django import forms

from .models import Review, ReviewTag


class ReviewForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=ReviewTag.objects.all(), required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Review
        fields = [
            'rating', 'quality_rating', 'price_rating', 'service_rating', 'space_rating',
            'content', 'tags',
        ]
