import hashlib
import re
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.db.models import Q
from apps.movies.models import Profile


class IndiMusicAuthBackend(BaseBackend):
    """
    Seamless Dual Authentication Backend:
    1. Authenticates against modern Django User passwords (PBKDF2).
    2. Seamlessly authenticates legacy 7,391 BoonEx Dolphin profiles using SHA1/Salt hashes.
    3. On successful legacy authentication, automatically provisions/links a Django User
       and upgrades their password to modern secure PBKDF2 hashing.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # 1. Try standard Django User authentication first
        django_user = User.objects.filter(
            Q(username__iexact=username) | Q(email__iexact=username)
        ).first()

        if django_user and django_user.check_password(password):
            return django_user

        # 2. Try legacy Profile from imported database
        profile = Profile.objects.filter(
            Q(nickname__iexact=username) | Q(email__iexact=username)
        ).first()

        if not profile or not profile.password_hash:
            return None

        # Verify password using Dolphin 7 hash methods
        if self._verify_dolphin_password(password, profile.password_hash, profile.salt):
            # Password matched! Upgrade/link to Django User
            user = profile.user
            if not user:
                # Check if a User with matching username or email already exists
                user = User.objects.filter(
                    Q(username__iexact=profile.nickname) | Q(email__iexact=profile.email)
                ).first()

            if not user:
                # Sanitize nickname for Django username constraints
                clean_uname = re.sub(r'[^a-zA-Z0-9_@+.-]', '_', profile.nickname or f"user_{profile.id}")[:150]
                # Avoid duplicate username collision
                base_uname = clean_uname
                counter = 1
                while User.objects.filter(username__iexact=clean_uname).exists():
                    clean_uname = f"{base_uname}_{counter}"[:150]
                    counter += 1

                user = User.objects.create(
                    username=clean_uname,
                    email=profile.email or "",
                    first_name=(profile.full_name or profile.nickname)[:150],
                )

            # Update password to Django PBKDF2 standard
            user.set_password(password)
            user.is_active = True
            user.save()

            # Link Profile to User
            profile.user = user
            profile.save(update_fields=["user"])

            return user

        return None

    def _verify_dolphin_password(self, password, stored_hash, salt):
        stored = stored_hash.lower().strip()
        salt = salt or ""

        # Method 1: sha1(password + salt)
        cand1 = hashlib.sha1((password + salt).encode('utf-8')).hexdigest()
        if cand1 == stored:
            return True

        # Method 2: sha1(md5(password) + salt)
        pwd_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
        cand2 = hashlib.sha1((pwd_md5 + salt).encode('utf-8')).hexdigest()
        if cand2 == stored:
            return True

        # Method 3: sha1(salt + password)
        cand3 = hashlib.sha1((salt + password).encode('utf-8')).hexdigest()
        if cand3 == stored:
            return True

        # Method 4: Plain sha1(password)
        cand4 = hashlib.sha1(password.encode('utf-8')).hexdigest()
        if cand4 == stored:
            return True

        # Method 5: Plain md5(password)
        cand5 = hashlib.md5(password.encode('utf-8')).hexdigest()
        if cand5 == stored:
            return True

        return False

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
