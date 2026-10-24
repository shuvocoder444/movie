import os
import re
import html
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db import connection, transaction
from apps.movies.models import Profile, Category, Movie, MovieComment, BlogPost


def parse_sql_row(row_str):
    """Parse a single SQL tuple string like 1, 'text', 'other' respecting quotes."""
    tokens = []
    current = []
    in_quote = False
    quote_char = None
    escaped = False

    for ch in row_str:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == '\\':
            escaped = True
        elif ch in ("'", '"'):
            if not in_quote:
                in_quote = True
                quote_char = ch
            elif quote_char == ch:
                in_quote = False
                quote_char = None
            else:
                current.append(ch)
        elif ch == ',' and not in_quote:
            tokens.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        tokens.append(''.join(current).strip())

    cleaned = []
    for t in tokens:
        if (t.startswith("'") and t.endswith("'")) or (t.startswith('"') and t.endswith('"')):
            val = t[1:-1]
            val = val.replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\')
            val = val.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
            cleaned.append(val)
        elif t.upper() == 'NULL':
            cleaned.append(None)
        else:
            cleaned.append(t)
    return cleaned


class Command(BaseCommand):
    help = "Import all movies, profiles, comments and blogs from indimusic_dolph40 (1).sql"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=r"E:\movie\indimusic_dolph40 (1).sql",
            help="Path to the SQL file",
        )

    def handle(self, *args, **options):
        sql_path = options["file"]
        if not os.path.exists(sql_path):
            self.stderr.write(f"File not found: {sql_path}")
            return

        self.stdout.write(f"Reading and importing data from {sql_path}...")

        # 1. Parse Profiles
        self.stdout.write("Parsing Profiles...")
        profiles_to_create = []
        profile_ids = set()

        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            in_profiles = False
            for line in f:
                if "INSERT INTO `Profiles`" in line or "INSERT INTO Profiles " in line:
                    in_profiles = True
                    continue
                if in_profiles:
                    if line.startswith("INSERT INTO") or line.startswith("CREATE TABLE") or line.startswith("LOCK TABLES") or line.startswith("--"):
                        if "Profiles" not in line:
                            break
                    line_s = line.strip()
                    if line_s.startswith("("):
                        end_idx = -2 if (line_s.endswith("),") or line_s.endswith(");")) else -1
                        row_content = line_s[1:end_idx]
                        row = parse_sql_row(row_content)
                        if len(row) >= 50:
                            try:
                                pid = int(row[0])
                                nickname = row[1] or ""
                                email = row[2] or ""
                                headline = row[10] or ""
                                desc = row[11] or ""
                                country = row[12] or ""
                                city = row[13] or ""
                                
                                # DateReg
                                reg_date = None
                                if row[16] and row[16] != "0000-00-00 00:00:00":
                                    try:
                                        reg_date = datetime.strptime(row[16], "%Y-%m-%d %H:%M:%S")
                                    except Exception:
                                        pass

                                avatar = int(row[35]) if (row[35] and row[35].isdigit()) else 0
                                full_name = row[50] if len(row) > 50 and row[50] else nickname

                                if pid not in profile_ids:
                                    profile_ids.add(pid)
                                    profiles_to_create.append(
                                        Profile(
                                            id=pid,
                                            nickname=nickname[:150],
                                            email=email[:255],
                                            headline=headline[:255],
                                            description=desc,
                                            country=country[:100],
                                            city=city[:100],
                                            avatar=avatar,
                                            full_name=full_name[:255],
                                            created_at=reg_date,
                                        )
                                    )
                            except Exception as e:
                                continue

        self.stdout.write(f"Inserting {len(profiles_to_create)} Profiles...")
        Profile.objects.bulk_create(profiles_to_create, ignore_conflicts=True, batch_size=1000)

        # 2. Parse RayVideoFiles
        self.stdout.write("Parsing RayVideoFiles (Movies & Videos)...")
        movies_to_create = []
        categories_dict = {}
        movie_ids = set()

        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            in_videos = False
            for line in f:
                if "INSERT INTO `RayVideoFiles`" in line or "INSERT INTO RayVideoFiles " in line:
                    in_videos = True
                    continue
                if in_videos:
                    if line.startswith("INSERT INTO") or line.startswith("CREATE TABLE") or line.startswith("LOCK TABLES") or line.startswith("--"):
                        if "RayVideoFiles" not in line:
                            break
                    line_s = line.strip()
                    if line_s.startswith("("):
                        end_idx = -2 if (line_s.endswith("),") or line_s.endswith(");")) else -1
                        row_content = line_s[1:end_idx]
                        row = parse_sql_row(row_content)
                        if len(row) >= 17:
                            try:
                                vid = int(row[0])
                                cat_raw = row[1] or ""
                                title = row[2] or f"Movie #{vid}"
                                uri = row[3] or ""
                                tags = row[4] or ""
                                desc = row[5] or ""
                                duration = int(row[6]) if (row[6] and str(row[6]).isdigit()) else 0
                                
                                # Date epoch
                                movie_date = None
                                if row[7] and str(row[7]).isdigit() and int(row[7]) > 0:
                                    try:
                                        movie_date = datetime.fromtimestamp(int(row[7]))
                                    except Exception:
                                        pass
                                
                                owner_id = int(row[8]) if (row[8] and str(row[8]).isdigit()) else None
                                views = int(row[9]) if (row[9] and str(row[9]).isdigit()) else 0
                                rating = float(row[10]) if row[10] else 0.0
                                rating_count = int(row[11]) if (row[11] and str(row[11]).isdigit()) else 0
                                cmts_count = int(row[12]) if (row[12] and str(row[12]).isdigit()) else 0
                                featured = bool(int(row[13])) if (row[13] and str(row[13]).isdigit()) else False
                                status = row[14] or "approved"
                                source = row[15] or ""
                                video_data = row[16] or ""

                                # Extract primary category
                                primary_cat = cat_raw.split(";")[0].strip() if cat_raw else "Featured"
                                if primary_cat and primary_cat not in categories_dict:
                                    categories_dict[primary_cat] = Category.objects.get_or_create(
                                        name=primary_cat,
                                        defaults={"slug": slugify(primary_cat) or "category"}
                                    )[0]

                                # Extract YouTube ID if embedded in video_data
                                yt_id = ""
                                if re.match(r"^[a-zA-Z0-9_-]{11}$", video_data.strip()):
                                    yt_id = video_data.strip()
                                else:
                                    # check unescaped and escaped
                                    unescaped_data = html.unescape(video_data)
                                    match = re.search(r"(?:youtube\.com\/(?:embed\/|v\/|watch\?v=)|youtu\.be\/|%2Fembed%2F|%2Fwatch%3Fv%3D)([a-zA-Z0-9_-]{11})", unescaped_data)
                                    if match:
                                        yt_id = match.group(1)

                                # Poster URL from embedly if available
                                poster_url = ""
                                if "image=" in video_data or "image=" in html.unescape(video_data):
                                    m_img = re.search(r'image=(http[s]?%3A%2F%2F[^&"\s]+|http[s]?:\/\/[^&"\s]+)', html.unescape(video_data))
                                    if m_img:
                                        poster_url = html.unescape(m_img.group(1)).replace("%3A", ":").replace("%2F", "/")

                                if vid not in movie_ids:
                                    movie_ids.add(vid)
                                    slug = slugify(uri or title)[:200] or f"movie-{vid}"
                                    movies_to_create.append(
                                        Movie(
                                            id=vid,
                                            title=title[:255],
                                            slug=slug,
                                            category_name=primary_cat,
                                            category=categories_dict.get(primary_cat),
                                            tags=tags,
                                            description=desc,
                                            duration=duration,
                                            created_at=movie_date,
                                            owner_id=owner_id if owner_id in profile_ids else None,
                                            views=views,
                                            rating=rating,
                                            rating_count=rating_count,
                                            comments_count=cmts_count,
                                            is_featured=featured,
                                            status=status[:50],
                                            source=source[:50],
                                            video_data=video_data,
                                            youtube_id=yt_id,
                                            poster_url=poster_url[:500],
                                        )
                                    )
                            except Exception as e:
                                continue

        self.stdout.write(f"Inserting {len(movies_to_create)} Movies...")
        Movie.objects.bulk_create(movies_to_create, ignore_conflicts=True, batch_size=1000)

        # 3. Parse bx_videos_cmts
        self.stdout.write("Parsing Comments (bx_videos_cmts)...")
        cmts_to_create = []
        cmt_ids = set()

        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            in_cmts = False
            for line in f:
                if "INSERT INTO `bx_videos_cmts`" in line or "INSERT INTO bx_videos_cmts " in line:
                    in_cmts = True
                    continue
                if in_cmts:
                    if line.startswith("INSERT INTO") or line.startswith("CREATE TABLE") or line.startswith("LOCK TABLES") or line.startswith("--"):
                        if "bx_videos_cmts" not in line:
                            break
                    line_s = line.strip()
                    if line_s.startswith("("):
                        end_idx = -2 if (line_s.endswith("),") or line_s.endswith(");")) else -1
                        row_content = line_s[1:end_idx]
                        row = parse_sql_row(row_content)
                        if len(row) >= 9:
                            try:
                                cid = int(row[0])
                                vid_id = int(row[2])
                                author_id = int(row[3]) if (row[3] and str(row[3]).isdigit()) else None
                                text = row[4] or ""
                                rate = int(row[6]) if (row[6] and str(row[6]).lstrip("-").isdigit()) else 0
                                cmt_time = None
                                if row[8] and row[8] != "0000-00-00 00:00:00":
                                    try:
                                        cmt_time = datetime.strptime(row[8], "%Y-%m-%d %H:%M:%S")
                                    except Exception:
                                        pass

                                if cid not in cmt_ids and vid_id in movie_ids:
                                    cmt_ids.add(cid)
                                    author_name = "Anonymous"
                                    cmts_to_create.append(
                                        MovieComment(
                                            id=cid,
                                            movie_id=vid_id,
                                            author_id=author_id if author_id in profile_ids else None,
                                            author_name=author_name,
                                            text=text,
                                            rating=rate,
                                            created_at=cmt_time,
                                        )
                                    )
                            except Exception:
                                continue

        self.stdout.write(f"Inserting {len(cmts_to_create)} Comments...")
        MovieComment.objects.bulk_create(cmts_to_create, ignore_conflicts=True, batch_size=1000)

        # 4. Parse bx_blogs_posts
        self.stdout.write("Parsing Blog Posts / Reviews (bx_blogs_posts)...")
        posts_to_create = []
        post_ids = set()

        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            in_blogs = False
            for line in f:
                if "INSERT INTO `bx_blogs_posts`" in line or "INSERT INTO bx_blogs_posts " in line:
                    in_blogs = True
                    continue
                if in_blogs:
                    if line.startswith("INSERT INTO") or line.startswith("CREATE TABLE") or line.startswith("LOCK TABLES") or line.startswith("--"):
                        if "bx_blogs_posts" not in line:
                            break
                    line_s = line.strip()
                    if line_s.startswith("("):
                        end_idx = -2 if (line_s.endswith("),") or line_s.endswith(");")) else -1
                        row_content = line_s[1:end_idx]
                        row = parse_sql_row(row_content)
                        if len(row) >= 8:
                            try:
                                pid = int(row[0])
                                owner_id = int(row[1]) if (row[1] and str(row[1]).isdigit()) else None
                                caption = row[2] or f"Blog #{pid}"
                                post_uri = row[3] or ""
                                post_text = row[4] or ""
                                
                                p_date = None
                                if row[5] and str(row[5]).isdigit() and int(row[5]) > 0:
                                    try:
                                        p_date = datetime.fromtimestamp(int(row[5]))
                                    except Exception:
                                        pass
                                
                                p_views = int(row[7]) if (row[7] and str(row[7]).isdigit()) else 0
                                p_tags = row[8] if len(row) > 8 and row[8] else ""

                                if pid not in post_ids:
                                    post_ids.add(pid)
                                    slug = slugify(post_uri or caption)[:200] or f"blog-{pid}"
                                    posts_to_create.append(
                                        BlogPost(
                                            id=pid,
                                            title=caption[:255],
                                            slug=slug,
                                            content=post_text,
                                            author_id=owner_id if owner_id in profile_ids else None,
                                            views=p_views,
                                            tags=p_tags[:255],
                                            created_at=p_date,
                                        )
                                    )
                            except Exception:
                                continue

        self.stdout.write(f"Inserting {len(posts_to_create)} Blog Posts...")
        BlogPost.objects.bulk_create(posts_to_create, ignore_conflicts=True, batch_size=500)

        self.stdout.write(self.style.SUCCESS("All data imported successfully!"))
