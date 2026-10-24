import re
from datetime import datetime, timezone
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify


class Profile(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="profile")
    nickname = models.CharField(max_length=150, default="", db_index=True)
    email = models.CharField(max_length=255, blank=True, default="", db_index=True)
    password_hash = models.CharField(max_length=128, blank=True, default="")
    salt = models.CharField(max_length=32, blank=True, default="")
    headline = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    avatar = models.IntegerField(default=0)
    full_name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["nickname"]

    def __str__(self):
        return self.full_name or self.nickname or f"User #{self.id}"

    @property
    def display_name(self):
        return self.full_name or self.nickname or f"Creator #{self.id}"

    @property
    def avatar_url(self):
        # Generates a nice deterministic avatar based on name or ID
        return f"https://api.dicebear.com/7.x/bottts/svg?seed={self.nickname or self.id}"

    @property
    def clean_headline(self):
        import html, re
        raw = html.unescape(self.headline or "")
        cleaned = re.sub(r"<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", cleaned).strip()

    @property
    def clean_description(self):
        import html, re
        raw = html.unescape(self.description or "")
        cleaned = re.sub(r"<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", cleaned).strip()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "category"
        super().save(*args, **kwargs)


class Movie(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, default="")
    category_name = models.CharField(max_length=100, blank=True, default="")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="movies"
    )
    tags = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    duration = models.IntegerField(default=0, help_text="Duration in seconds or ms")
    created_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="movies"
    )
    views = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default="approved")
    source = models.CharField(max_length=50, blank=True, default="")
    video_data = models.TextField(blank=True, default="")
    youtube_id = models.CharField(max_length=100, blank=True, default="")
    poster_url = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-views", "-rating", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:200] or f"movie-{self.id}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("movie_detail", kwargs={"pk": self.id})

    @property
    def clean_youtube_id(self):
        if self.youtube_id:
            return self.youtube_id
        # Check in video_data
        data = self.video_data or ""
        # Check standard 11-char ID
        if re.match(r"^[a-zA-Z0-9_-]{11}$", data.strip()):
            return data.strip()
        # Check embedly or youtube urls
        match = re.search(r"(?:youtube\.com\/(?:embed\/|v\/|watch\?v=)|youtu\.be\/|%2Fembed%2F|%2Fwatch%3Fv%3D)([a-zA-Z0-9_-]{11})", data)
        if match:
            return match.group(1)
        return ""

    @property
    def b2_video_mp4_url(self):
        from django.conf import settings
        base = getattr(settings, "BACKBLAZE_B2_BASE_URL", "").rstrip("/")
        if base:
            return f"{base}/{self.id}.mp4"
        return ""

    @property
    def b2_video_webm_url(self):
        from django.conf import settings
        base = getattr(settings, "BACKBLAZE_B2_BASE_URL", "").rstrip("/")
        if base:
            return f"{base}/{self.id}.webm"
        return ""

    @property
    def b2_thumbnail_url(self):
        from django.conf import settings
        base = getattr(settings, "BACKBLAZE_B2_BASE_URL", "").rstrip("/")
        if base:
            return f"{base}/{self.id}.jpg"
        return ""

    @property
    def b2_thumbnail_small_url(self):
        from django.conf import settings
        base = getattr(settings, "BACKBLAZE_B2_BASE_URL", "").rstrip("/")
        if base:
            return f"{base}/{self.id}_small.jpg"
        return ""

    @property
    def get_embed_url(self):
        yt = self.clean_youtube_id
        if yt:
            return f"https://www.youtube.com/embed/{yt}?autoplay=1&rel=0&modestbranding=1"
        return ""

    @property
    def get_thumbnail_url(self):
        if self.poster_url:
            return self.poster_url
        yt = self.clean_youtube_id
        if yt:
            return f"https://img.youtube.com/vi/{yt}/hqdefault.jpg"
        if self.b2_thumbnail_url:
            return self.b2_thumbnail_url
        
        # High quality gradient cinematic fallback based on category / ID
        cat = (self.category_name or "Cinema").lower()
        if "rock" in cat or "metal" in cat:
            return f"https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80"
        elif "pop" in cat or "indie" in cat:
            return f"https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80"
        elif "country" in cat or "folk" in cat:
            return f"https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=600&auto=format&fit=crop&q=80"
        elif "hip hop" in cat or "r&b" in cat:
            return f"https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=600&auto=format&fit=crop&q=80"
        return f"https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&auto=format&fit=crop&q=80"

    @property
    def formatted_duration(self):
        secs = self.duration
        if secs > 10000:
            secs = int(secs / 1000)
        if secs <= 0:
            return "HD"
        minutes = secs // 60
        seconds = secs % 60
        hours = minutes // 60
        if hours > 0:
            return f"{hours}h {minutes % 60}m"
        return f"{minutes}:{seconds:02d}"

    @property
    def formatted_views(self):
        v = self.views
        if v >= 1000000:
            return f"{v / 1000000:.1f}M"
        if v >= 1000:
            return f"{v / 1000:.1f}K"
        return str(v)

    @property
    def clean_description(self):
        import html, re
        raw = html.unescape(self.description or "")
        cleaned = re.sub(r"<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", cleaned).strip()


class MovieComment(models.Model):
    id = models.IntegerField(primary_key=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="comments")
    author_name = models.CharField(max_length=150, blank=True, default="Anonymous")
    text = models.TextField()
    rating = models.IntegerField(default=0)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Comment on {self.movie.title} by {self.author_name}"

    @property
    def clean_text(self):
        import html, re
        raw = html.unescape(self.text or "")
        # Strip all HTML tags like <p>, <strong>, <em>, <a href>
        cleaned = re.sub(r"<[^>]+>", " ", raw)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned


class BlogPost(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, default="")
    content = models.TextField()
    author = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="blog_posts")
    author_name = models.CharField(max_length=150, blank=True, default="Editor")
    views = models.IntegerField(default=0)
    tags = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"pk": self.id})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:200] or f"post-{self.id}"
        super().save(*args, **kwargs)


class SiteSetting(models.Model):
    """Global Website Settings & Customizations (Singleton)."""
    site_name = models.CharField(max_length=150, default="IndiMusic TV", help_text="Website name")
    tagline = models.CharField(max_length=255, default="We Are Music, Together.", help_text="Hero tagline / slogan")
    logo = models.ImageField(upload_to="branding/", blank=True, null=True, help_text="Upload custom header/footer logo")
    favicon = models.ImageField(upload_to="branding/", blank=True, null=True, help_text="Upload custom browser favicon (.ico/.png)")

    # Contact Info
    phone_number = models.CharField(max_length=50, blank=True, default="+1 (800) 555-INDI", help_text="Customer support phone number")
    contact_email = models.EmailField(blank=True, default="support@indimusictv.com", help_text="Support / business email")
    address = models.TextField(blank=True, default="123 Music Boulevard, Suite 500, New York, NY 10001, USA", help_text="Physical / studio address")

    # Social Media Accounts
    facebook_url = models.URLField(blank=True, default="https://facebook.com/indimusictv")
    twitter_url = models.URLField(blank=True, default="https://twitter.com/indimusictv")
    instagram_url = models.URLField(blank=True, default="https://instagram.com/indimusictv")
    youtube_url = models.URLField(blank=True, default="https://youtube.com/@indimusictv")
    tiktok_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")

    # Header & Footer text
    header_announcement = models.CharField(max_length=255, blank=True, default="", help_text="Optional banner notice at the top of the header")
    footer_about_text = models.TextField(
        blank=True,
        default="IndiMusic TV is a premier music video and independent film streaming platform — 'We Are Music, Together.' Powered by over 2,780+ videos & films and 7,400+ creative artists and filmmakers.",
        help_text="Short bio shown in the footer"
    )
    copyright_text = models.CharField(max_length=255, blank=True, default="© 2026 IndiMusic TV. All rights reserved.", help_text="Footer copyright line")

    class Meta:
        verbose_name = "Website Setting & Customization"
        verbose_name_plural = "Website Settings & Customizations"

    def __str__(self):
        return f"{self.site_name} Configuration"

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def logo_url(self):
        if self.logo and hasattr(self.logo, "url"):
            try:
                return self.logo.url
            except Exception:
                pass
        from django.templatetags.static import static
        return static("img/branding/indimusic-logo.png")

    @property
    def favicon_url(self):
        if self.favicon and hasattr(self.favicon, "url"):
            try:
                return self.favicon.url
            except Exception:
                pass
        from django.templatetags.static import static
        return static("img/favicon/favicon.ico")

