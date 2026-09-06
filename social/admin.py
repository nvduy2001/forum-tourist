from django.contrib import admin

from .models import CommentLike, PlaceFollow, ReviewVote, UserFollow

admin.site.register(UserFollow)
admin.site.register(PlaceFollow)
admin.site.register(ReviewVote)
admin.site.register(CommentLike)
