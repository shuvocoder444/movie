from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView, DetailView, ListView
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from web_project import TemplateLayout
from web_project.template_helpers.theme import TemplateHelper
from .models import Movie, Category, Profile, MovieComment, BlogPost, SiteSetting



class BaseMovieView:
    """Helper mixin to initialize Vuexy template layout."""
    def get_layout_context(self, request, context=None):
        if context is None:
            context = {}
        context = TemplateLayout.init(self, context)
        context.update({
            "layout_path": TemplateHelper.set_layout("layout_front.html", context),
            "is_front": True,
            "is_navbar": True,
            "is_footer": True,
            "content_layout": "wide",
            "style": "light",  # Default light (sada) mode with cinematic dark toggle!
        })
        return context

    @staticmethod
    def get_pagination_window(paginator, page_obj, window_size=10):
        """Returns a sliding window of page numbers (e.g. 1..10) around the current page."""
        total = paginator.num_pages
        current = page_obj.number
        if total <= window_size:
            start = 1
            end = total
        else:
            start = max(1, current - (window_size // 2))
            end = start + window_size - 1
            if end > total:
                end = total
                start = max(1, end - window_size + 1)
        return range(start, end + 1)


class MovieLandingView(BaseMovieView, View):
    """Movie Portal Landing Page."""
    def get(self, request):
        context = self.get_layout_context(request)

        # 1. Hero Featured Movies (with valid video/youtube)
        hero_movies = (
            Movie.objects.filter(youtube_id__gt="", views__gt=100)
            .order_by("-views")[:6]
        )
        if not hero_movies.exists():
            hero_movies = Movie.objects.all()[:6]

        # 2. Trending Movies (Highest Views)
        trending_movies = Movie.objects.all().order_by("-views")[:12]

        # 3. Top Rated Movies
        top_rated_movies = Movie.objects.filter(rating__gte=4.0).order_by("-rating", "-views")[:12]

        # 4. Latest Added Movies
        latest_movies = Movie.objects.filter(created_at__isnull=False).order_by("-created_at")[:12]

        # 5. Categories with counts
        top_categories = (
            Category.objects.annotate(movie_cnt=Count("movies"))
            .filter(movie_cnt__gt=0)
            .order_by("-movie_cnt")[:12]
        )

        # 6. Featured Creators/Directors
        featured_creators = (
            Profile.objects.annotate(num_movies=Count("movies"))
            .filter(num_movies__gt=0)
            .order_by("-num_movies")[:8]
        )

        # 7. Recent Movie Reviews / Blog Posts
        blog_posts = BlogPost.objects.all().order_by("-created_at")[:4]

        # 8. Stats
        total_movies = Movie.objects.count()
        total_creators = Profile.objects.count()
        total_categories = Category.objects.count()

        context.update({
            "hero_movies": hero_movies,
            "hero_featured": hero_movies.first() if hero_movies else None,
            "trending_movies": trending_movies,
            "top_rated_movies": top_rated_movies,
            "latest_movies": latest_movies,
            "top_categories": top_categories,
            "featured_creators": featured_creators,
            "blog_posts": blog_posts,
            "total_movies": total_movies,
            "total_creators": total_creators,
            "total_categories": total_categories,
        })
        return render(request, "movies/landing.html", context)


class MovieCatalogView(BaseMovieView, View):
    """Movie Explore and Catalog Page with Filters, Search and Sorting."""
    def get(self, request):
        context = self.get_layout_context(request)

        query = request.GET.get("q", "").strip()
        cat_slug = request.GET.get("category", "").strip()
        sort_by = request.GET.get("sort", "views")
        min_rating = request.GET.get("rating", "")

        movies = Movie.objects.all()

        if query:
            movies = movies.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__icontains=query)
                | Q(category_name__icontains=query)
            )

        active_category = None
        if cat_slug:
            active_category = Category.objects.filter(slug=cat_slug).first()
            if active_category:
                movies = movies.filter(Q(category=active_category) | Q(category_name__iexact=active_category.name))

        if min_rating and min_rating.isdigit():
            movies = movies.filter(rating__gte=float(min_rating))

        # Sorting
        if sort_by == "rating":
            movies = movies.order_by("-rating", "-views")
        elif sort_by == "newest":
            movies = movies.order_by("-created_at", "-id")
        elif sort_by == "title":
            movies = movies.order_by("title")
        else:  # default 'views'
            movies = movies.order_by("-views", "-rating")

        # Pagination: 50 videos per page as requested
        paginator = Paginator(movies, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        page_range = self.get_pagination_window(paginator, page_obj, window_size=10)

        categories = (
            Category.objects.annotate(movie_cnt=Count("movies"))
            .filter(movie_cnt__gt=0)
            .order_by("-movie_cnt")
        )

        context.update({
            "page_obj": page_obj,
            "page_range": page_range,
            "movies": page_obj.object_list,
            "categories": categories,
            "active_category": active_category,
            "query": query,
            "sort_by": sort_by,
            "min_rating": min_rating,
            "total_count": paginator.count,
        })
        return render(request, "movies/catalog.html", context)


class MovieDetailView(BaseMovieView, View):
    """Movie Player & Details View with Comments and Recommendations."""
    def get(self, request, pk, slug=None):
        context = self.get_layout_context(request)
        movie = get_object_or_404(Movie, pk=pk)

        # Increment view count
        Movie.objects.filter(pk=pk).update(views=movie.views + 1)
        movie.views += 1

        # Related movies
        related_movies = (
            Movie.objects.filter(
                Q(category_name=movie.category_name) | Q(tags__icontains=movie.category_name)
            )
            .exclude(pk=pk)
            .order_by("-views")[:6]
        )

        # Comments: filter out empty tags / spam
        raw_comments = movie.comments.all().select_related("author").order_by("-created_at")[:60]
        comments = [c for c in raw_comments if c.clean_text][:30]

        context.update({
            "movie": movie,
            "related_movies": related_movies,
            "comments": comments,
            "comments_count": len(comments),
        })
        return render(request, "movies/detail.html", context)

    def post(self, request, pk, slug=None):
        movie = get_object_or_404(Movie, pk=pk)
        text = request.POST.get("comment", "").strip()
        author_name = request.POST.get("author_name", "Anonymous Movie Buff").strip()

        if text:
            MovieComment.objects.create(
                movie=movie,
                author_name=author_name or "Guest",
                text=text,
                rating=5,
            )
            Movie.objects.filter(pk=pk).update(comments_count=movie.comments_count + 1)

        return redirect("movie_detail", pk=movie.id, slug=movie.slug or f"movie-{movie.id}")


class CreatorListView(BaseMovieView, View):
    """List of Movie Creators & Directors."""
    def get(self, request):
        context = self.get_layout_context(request)
        creators = (
            Profile.objects.annotate(num_movies=Count("movies"))
            .filter(num_movies__gt=0)
            .order_by("-num_movies")
        )
        paginator = Paginator(creators, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        page_range = self.get_pagination_window(paginator, page_obj, window_size=10)

        context.update({
            "page_obj": page_obj,
            "page_range": page_range,
            "creators": page_obj.object_list,
        })
        return render(request, "movies/creator_list.html", context)


class CreatorDetailView(BaseMovieView, View):
    """Creator Profile & Filmography."""
    def get(self, request, pk):
        context = self.get_layout_context(request)
        creator = get_object_or_404(Profile, pk=pk)
        movies = creator.movies.all().order_by("-views")
        
        paginator = Paginator(movies, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        page_range = self.get_pagination_window(paginator, page_obj, window_size=10)

        context.update({
            "creator": creator,
            "page_obj": page_obj,
            "page_range": page_range,
            "movies": page_obj.object_list,
            "movies_count": paginator.count,
        })
        return render(request, "movies/creator_detail.html", context)


class BlogPostListView(BaseMovieView, View):
    """Movie News, Blogs & Reviews."""
    def get(self, request):
        context = self.get_layout_context(request)
        blogs = BlogPost.objects.all().order_by("-created_at")
        paginator = Paginator(blogs, 20)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        page_range = self.get_pagination_window(paginator, page_obj, window_size=10)

        context.update({
            "page_obj": page_obj,
            "page_range": page_range,
            "blogs": page_obj.object_list,
        })
        return render(request, "movies/blog_list.html", context)


class BlogPostDetailView(BaseMovieView, View):
    """Blog / Review Article Detail."""
    def get(self, request, pk, slug=None):
        context = self.get_layout_context(request)
        post = get_object_or_404(BlogPost, pk=pk)
        BlogPost.objects.filter(pk=pk).update(views=post.views + 1)
        post.views += 1
        recent_posts = BlogPost.objects.exclude(pk=pk).order_by("-created_at")[:5]

        context.update({
            "post": post,
            "recent_posts": recent_posts,
        })
        return render(request, "movies/blog_detail.html", context)


def quick_search_api(request):
    """JSON search suggestions for the navbar search input."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    results = []
    movies = Movie.objects.filter(
        Q(title__icontains=q) | Q(category_name__icontains=q)
    )[:8]

    for m in movies:
        results.append({
            "id": m.id,
            "title": m.title,
            "category": m.category_name,
            "thumbnail": m.get_thumbnail_url,
            "duration": m.formatted_duration,
            "url": m.get_absolute_url(),
        })

    return JsonResponse({"results": results})


class UserLoginView(BaseMovieView, View):
    """User Login supporting both legacy 7,391 database users and new users."""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("movie_landing")
        context = self.get_layout_context(request)
        context["next"] = request.GET.get("next", "")
        return render(request, "movies/login.html", context)

    def post(self, request):
        username_or_email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me")
        next_url = request.POST.get("next", "")

        user = authenticate(request, username=username_or_email, password=password)
        if user is not None:
            login(request, user)
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  # 2 weeks
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect("movie_landing")
        else:
            messages.error(request, "Invalid username/email or password. Please try again.")
            context = self.get_layout_context(request)
            context["username"] = username_or_email
            context["next"] = next_url
            return render(request, "movies/login.html", context)


class UserRegisterView(BaseMovieView, View):
    """New User Registration."""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("movie_landing")
        context = self.get_layout_context(request)
        return render(request, "movies/register.html", context)

    def post(self, request):
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        full_name = request.POST.get("full_name", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        context = self.get_layout_context(request)
        context.update({"username": username, "email": email, "full_name": full_name})

        # Basic validations
        if not username or not email or not password:
            messages.error(request, "All required fields must be filled.")
            return render(request, "movies/register.html", context)

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, "movies/register.html", context)

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "movies/register.html", context)

        if User.objects.filter(username__iexact=username).exists() or Profile.objects.filter(nickname__iexact=username).exists():
            messages.error(request, "Username is already taken. Please choose another.")
            return render(request, "movies/register.html", context)

        if User.objects.filter(email__iexact=email).exists() or Profile.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, "movies/register.html", context)

        # Create Django User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name[:150] or username,
        )

        # Find next available Profile ID
        max_id = Profile.objects.order_by("-id").values_list("id", flat=True).first() or 0
        profile = Profile.objects.create(
            id=max_id + 1,
            user=user,
            nickname=username,
            email=email,
            full_name=full_name or username,
        )

        login(request, user)
        messages.success(request, f"Welcome to IndiMusic TV, {user.first_name or user.username}! Your account has been created.")
        return redirect("movie_landing")


class UserLogoutView(View):
    """User Logout."""
    def get(self, request):
        logout(request)
        messages.info(request, "You have been signed out.")
        return redirect("movie_landing")

    def post(self, request):
        return self.get(request)


class GoogleLoginView(BaseMovieView, View):
    """Google / Gmail Authentication handler."""
    def get(self, request):
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        # If real OAuth client credentials are configured, redirect to Google OAuth
        if client_id and client_id.strip() and client_id != "YOUR_GOOGLE_CLIENT_ID":
            redirect_uri = request.build_absolute_uri(reverse("google_callback"))
            google_auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"scope=openid%20email%20profile&"
                f"redirect_uri={redirect_uri}&"
                f"access_type=offline&prompt=select_account"
            )
            return redirect(google_auth_url)

        # Standard / Instant Gmail sign in & registration
        context = self.get_layout_context(request)
        context["next"] = request.GET.get("next", "")
        return render(request, "movies/gmail_login.html", context)

    def post(self, request):
        import re
        gmail = request.POST.get("gmail", "").strip().lower()
        full_name = request.POST.get("full_name", "").strip()

        if not gmail or "@" not in gmail:
            messages.error(request, "Please enter a valid Gmail address.")
            return redirect("google_login")

        # Extract base username from email address
        uname = gmail.split("@")[0]
        user = User.objects.filter(Q(email__iexact=gmail) | Q(username__iexact=uname)).first()

        if not user:
            # Check legacy Profile
            profile = Profile.objects.filter(Q(email__iexact=gmail) | Q(nickname__iexact=uname)).first()
            if profile and profile.user:
                user = profile.user
            elif profile:
                user = User.objects.create_user(
                    username=profile.nickname or uname[:150],
                    email=gmail,
                    first_name=full_name or profile.full_name or uname.replace(".", " ").title(),
                )
                profile.user = user
                profile.save()
            else:
                # Create brand new user & profile
                base_uname = uname
                clean_uname = re.sub(r'[^a-zA-Z0-9_@+.-]', '_', base_uname)[:150]
                counter = 1
                while User.objects.filter(username__iexact=clean_uname).exists():
                    clean_uname = f"{base_uname}_{counter}"[:150]
                    counter += 1

                user = User.objects.create_user(
                    username=clean_uname,
                    email=gmail,
                    first_name=full_name or uname.replace(".", " ").title(),
                )
                max_id = Profile.objects.order_by("-id").values_list("id", flat=True).first() or 0
                Profile.objects.create(
                    id=max_id + 1,
                    user=user,
                    nickname=clean_uname,
                    email=gmail,
                    full_name=full_name or uname.replace(".", " ").title(),
                )

        login(request, user, backend="apps.movies.auth_backend.IndiMusicAuthBackend")
        messages.success(request, f"Signed in with Google ({gmail}) successfully!")
        next_url = request.POST.get("next", "")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect("movie_landing")


