"""URLs of the example app."""

from django.urls import path

from samples import views

urlpatterns = [
    path("", views.SampleList.as_view(), name="sample-list"),
    path("samples/add/", views.SampleCreate.as_view(), name="sample-add"),
    path("samples/<int:pk>/", views.SampleUpdate.as_view(), name="sample-change"),
    path("plain/", views.PlainFormView.as_view(), name="plain-form"),
]
