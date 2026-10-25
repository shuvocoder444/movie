import base64
import json
import urllib.request
from django.core.cache import cache

def get_b2_download_token():
    """
    Retrieves or generates a cached Backblaze B2 download authorization token (valid 24h).
    Allows smooth HTML5 video streaming from the private IndiMusicTVAssets bucket.
    """
    cached_token = cache.get("b2_download_auth_token")
    if cached_token:
        return cached_token

    try:
        from .models import SiteSetting
        setting = SiteSetting.load()
        key_id = setting.b2_key_id or "005ae8312fcb01f0000000001"
        app_key = setting.b2_application_key or "K005NQSN0QMc0pGQRllCC95L6vfgCFI"
        bucket_id = setting.b2_bucket_id or "2a5e486371326f9cab10011f"

        auth_string = f"{key_id}:{app_key}"
        basic_auth = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

        req = urllib.request.Request(
            "https://api.backblazeb2.com/b2api/v2/b2_authorize_account",
            headers={"Authorization": f"Basic {basic_auth}"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            api_url = data.get("apiUrl")
            auth_token = data.get("authorizationToken")
            download_url = data.get("downloadUrl", "https://f005.backblazeb2.com")

            # Update download url in setting if changed
            if setting.b2_download_url != download_url:
                setting.b2_download_url = download_url
                setting.save(update_fields=["b2_download_url"])

            # Request 24h download authorization for the whole bucket
            auth_req = urllib.request.Request(
                f"{api_url}/b2api/v2/b2_get_download_authorization",
                data=json.dumps({
                    "bucketId": bucket_id,
                    "fileNamePrefix": "",
                    "validDurationInSeconds": 86400
                }).encode("utf-8"),
                headers={
                    "Authorization": auth_token,
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(auth_req, timeout=8) as auth_resp:
                auth_data = json.loads(auth_resp.read().decode("utf-8"))
                down_token = auth_data.get("authorizationToken")
                if down_token:
                    # Cache token for 20 hours (72,000 seconds)
                    cache.set("b2_download_auth_token", down_token, timeout=72000)
                    return down_token
    except Exception as e:
        print(f"Backblaze B2 Auth Error: {e}")

    return ""

