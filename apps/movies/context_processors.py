from .models import SiteSetting


def site_settings_processor(request):
    """Makes site_settings globally available to all templates."""
    try:
        setting = SiteSetting.load()
    except Exception:
        setting = None
    return {
        "site_settings": setting,
    }
