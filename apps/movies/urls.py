from django.urls import path
from .views import (
    MovieLandingView,
    MovieCatalogView,
    MovieDetailView,
    CreatorListView,
    CreatorDetailView,
    BlogPostListView,
    BlogPostDetailView,
    quick_search_api,
    UserLoginView,
    UserRegisterView,
    UserLogoutView,
    GoogleLoginView,
)

urlpatterns = [
    path("", MovieLandingView.as_view(), name="movie_landing"),
    path("movies/", MovieCatalogView.as_view(), name="movie_catalog"),
    path("movies/<int:pk>/", MovieDetailView.as_view(), name="movie_detail"),
    path("movies/<int:pk>/<slug:slug>/", MovieDetailView.as_view(), name="movie_detail_slug"),
    path("creators/", CreatorListView.as_view(), name="creator_list"),
    path("creators/<int:pk>/", CreatorDetailView.as_view(), name="creator_detail"),
    path("blogs/", BlogPostListView.as_view(), name="blog_list"),
    path("blogs/<int:pk>/", BlogPostDetailView.as_view(), name="blog_detail"),
    path("blogs/<int:pk>/<slug:slug>/", BlogPostDetailView.as_view(), name="blog_detail_slug"),
    path("api/search/", quick_search_api, name="quick_search_api"),
    path("login/", UserLoginView.as_view(), name="user_login"),
    path("register/", UserRegisterView.as_view(), name="user_register"),
    path("logout/", UserLogoutView.as_view(), name="user_logout"),
    path("auth/google/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/google/callback/", GoogleLoginView.as_view(), name="google_callback"),
]

