from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from places.models import Place
from reviews.models import Comment, Review

from .models import CommentLike, PlaceFollow, ReviewVote, UserFollow

User = get_user_model()


@login_required
@require_POST
def toggle_follow_user(request, username):
    target = get_object_or_404(User, username=username)
    if target.id == request.user.id:
        return JsonResponse({'error': 'cannot follow yourself'}, status=400)

    follow = UserFollow.objects.filter(follower=request.user, following=target).first()
    if follow:
        follow.delete()
        followed = False
    else:
        UserFollow.objects.create(follower=request.user, following=target)
        followed = True

    return JsonResponse({'followed': followed, 'follower_count': target.followers.count()})


@login_required
@require_POST
def toggle_follow_place(request, place_id):
    place = get_object_or_404(Place, pk=place_id)

    follow = PlaceFollow.objects.filter(user=request.user, place=place).first()
    if follow:
        follow.delete()
        followed = False
    else:
        PlaceFollow.objects.create(user=request.user, place=place)
        followed = True

    return JsonResponse({'followed': followed, 'follower_count': place.followers.count()})


@login_required
@require_POST
def toggle_review_vote(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    vote = ReviewVote.objects.filter(user=request.user, review=review).first()
    if vote:
        vote.delete()
        voted = False
    else:
        ReviewVote.objects.create(user=request.user, review=review)
        voted = True

    return JsonResponse({'voted': voted, 'vote_count': review.helpful_votes.count()})


@login_required
@require_POST
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)

    like = CommentLike.objects.filter(user=request.user, comment=comment).first()
    if like:
        like.delete()
        liked = False
    else:
        CommentLike.objects.create(user=request.user, comment=comment)
        liked = True

    return JsonResponse({'liked': liked, 'like_count': comment.likes.count()})
