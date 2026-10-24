from django.contrib import admin
from .models import Profile, Category, Movie, MovieComment, BlogPost


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "nickname", "full_name", "country", "city")
    search_fields = ("nickname", "full_name", "email")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category_name", "views", "rating", "is_featured", "created_at")
    list_filter = ("category_name", "is_featured", "status")
    search_fields = ("title", "description", "tags")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(MovieComment)
class MovieCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "movie", "author_name", "rating", "created_at")
    search_fields = ("text", "author_name")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author_name", "views", "created_at")
    search_fields = ("title", "content")
