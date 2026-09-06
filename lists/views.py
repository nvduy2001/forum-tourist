from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from places.models import Place

from .models import List, ListItem


class ListListView(LoginRequiredMixin, ListView):
    model = List
    context_object_name = 'lists'

    def get_queryset(self):
        return List.objects.filter(user=self.request.user)


class ListDetailView(DetailView):
    model = List
    context_object_name = 'list'

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return List.objects.filter(Q(is_public=True) | Q(user=user))
        return List.objects.filter(is_public=True)


class ListCreateView(LoginRequiredMixin, CreateView):
    model = List
    fields = ['name', 'description', 'is_public']

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ListOwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def get_queryset(self):
        return List.objects.filter(user=self.request.user)

    def test_func(self):
        return self.get_object().user_id == self.request.user.id


class ListUpdateView(ListOwnerRequiredMixin, UpdateView):
    model = List
    fields = ['name', 'description', 'is_public']


class ListDeleteView(ListOwnerRequiredMixin, DeleteView):
    model = List
    success_url = '/'


@login_required
@require_POST
def add_place_to_list(request, list_id, place_id):
    travel_list = get_object_or_404(List, pk=list_id, user=request.user)
    place = get_object_or_404(Place, pk=place_id)

    item, created = ListItem.objects.get_or_create(
        list=travel_list, place=place, defaults={'note': request.POST.get('note', '')}
    )
    return JsonResponse({'item_id': item.id, 'created': created})


@login_required
@require_POST
def remove_place_from_list(request, list_id, place_id):
    travel_list = get_object_or_404(List, pk=list_id, user=request.user)
    deleted, _ = ListItem.objects.filter(list=travel_list, place_id=place_id).delete()
    return JsonResponse({'removed': deleted > 0})
