from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, Category, Movie, MovieComment, BlogPost, SiteSetting

# Modernize Admin Branding
admin.site.site_header = "IndiMusic TV Administration"
admin.site.site_title = "IndiMusic TV Admin Portal"
admin.site.index_title = "Platform Management Dashboard"


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("site_name", "tagline", "phone_number", "contact_email", "logo_preview")
    
    fieldsets = (
        ("🎨 Branding & Identity", {
            "description": "Customize your website logo, favicon, name and hero tagline.",
            "fields": ("site_name", "tagline", "logo", "favicon"),
        }),
        ("📞 Contact Details & Physical Location", {
            "description": "These details appear in the website header, footer, and contact sections.",
            "fields": ("phone_number", "contact_email", "address"),
        }),
        ("🌐 Social Media Accounts", {
            "description": "Enter the full URLs for your official social channels.",
            "fields": ("facebook_url", "twitter_url", "instagram_url", "youtube_url", "tiktok_url", "linkedin_url"),
        }),
        ("📝 Header Announcement & Footer Text", {
            "description": "Customize announcement banners, footer about biography, and copyright statement.",
            "fields": ("header_announcement", "footer_about_text", "copyright_text"),
        }),
        ("🎬 Hero Section & Live Sidebar", {
            "description": "Control the visibility and title of the Latest Videos sidebar next to the Live Stream in the hero section.",
            "fields": ("show_hero_sidebar", "hero_sidebar_title"),
        }),
        ("☁️ Backblaze B2 Video Cloud Storage", {
            "description": "Configure your Backblaze B2 credentials to seamlessly stream 199+ GB of video assets from your private bucket.",
            "fields": ("b2_key_id", "b2_application_key", "b2_bucket_id", "b2_bucket_name", "b2_download_url"),
        }),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height: 32px; background: #000; padding: 2px 6px; border-radius: 4px;" />', obj.logo.url)
        return format_html('<span style="color: #64748b;">Default Logo</span>')
    logo_preview.short_description = "Active Logo"

    def has_add_permission(self, request):
        # Enforce singleton - only one settings record
        if SiteSetting.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "nickname", "full_name", "email", "country", "city")
    search_fields = ("nickname", "full_name", "email")
    list_filter = ("country",)


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

