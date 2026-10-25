import os
import sys
import re
import json
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.movies.models import Movie

def sync_assets():
    b2_file_path = os.path.join(os.path.dirname(__file__), 'b2_files.json')
    if not os.path.exists(b2_file_path):
        print(f"Error: {b2_file_path} not found!")
        return

    with open(b2_file_path, 'r', encoding='utf-8') as f:
        files = json.load(f)

    b2_video_ids = set()
    b2_poster_ids = set()

    for fn in files:
        m = re.match(r'^(\d+)(_small|_small_2x)?\.([a-zA-Z0-9]+)$', fn)
        if m:
            mid = int(m.group(1))
            ext = m.group(3).lower()
            if ext in {'mp4', 'm4v', 'webm', 'ogv', 'flv', 'mp42'}:
                b2_video_ids.add(mid)
            elif ext in {'jpg', 'jpeg', 'png'}:
                b2_poster_ids.add(mid)

    print(f"Identified {len(b2_video_ids)} IDs with B2 videos.")
    print(f"Identified {len(b2_poster_ids)} IDs with B2 posters.")

    all_movies = list(Movie.objects.all())
    updates = []
    
    video_count = 0
    b2_video_count = 0
    b2_poster_count = 0

    for m in all_movies:
        changed = False
        is_b2_vid = m.id in b2_video_ids
        is_b2_img = m.id in b2_poster_ids
        is_yt = bool(m.clean_youtube_id)
        has_any_video = is_b2_vid or is_yt

        if m.has_b2_video != is_b2_vid:
            m.has_b2_video = is_b2_vid
            changed = True
        if m.has_b2_poster != is_b2_img:
            m.has_b2_poster = is_b2_img
            changed = True
        if m.has_video != has_any_video:
            m.has_video = has_any_video
            changed = True

        if is_b2_vid:
            b2_video_count += 1
        if is_b2_img:
            b2_poster_count += 1
        if has_any_video:
            video_count += 1

        if changed:
            updates.append(m)

    if updates:
        Movie.objects.bulk_update(updates, ['has_b2_video', 'has_b2_poster', 'has_video'], batch_size=500)
        print(f"Successfully updated {len(updates)} movies in DB.")
    else:
        print("All movies already in sync.")

    print(f"Total Movies: {len(all_movies)}")
    print(f"Total Playable (has_video=True): {video_count}")
    print(f"Total with Backblaze B2 Videos: {b2_video_count}")
    print(f"Total with Backblaze B2 Posters: {b2_poster_count}")

if __name__ == '__main__':
    sync_assets()

