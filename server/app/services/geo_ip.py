import geoip2.database
import maxminddb
from app.config import settings


class GeoIPService:
    _reader = None

    @classmethod
    def get_reader(cls):
        if cls._reader is None:
            try:
                cls._reader = maxminddb.open_database(settings.GEOIP_DB_PATH)
            except Exception:
                return None
        return cls._reader

    @classmethod
    def get_country_code(cls, ip_address: str) -> str:
        if not ip_address:
            return "XX"
        
        if ip_address.startswith(("127.", "10.", "172.16.", "192.168.", "localhost")):
            return "XX"
        
        try:
            reader = cls.get_reader()
            if reader:
                response = reader.get(ip_address)
                if response and "country" in response:
                    return response["country"].get("iso_code", "XX")
        except Exception:
            pass
        
        return "XX"

    @classmethod
    def get_country_flag(cls, country_code: str) -> str:
        flag_map = {
            "US": "🇺🇸", "GB": "🇬🇧", "IN": "🇮🇳", "DE": "🇩🇪", "FR": "🇫🇷",
            "JP": "🇯🇵", "CN": "🇨🇳", "BR": "🇧🇷", "CA": "🇨🇦", "AU": "🇦🇺",
            "RU": "🇷🇺", "KR": "🇰🇷", "NL": "🇳🇱", "SE": "🇸🇪", "SG": "🇸🇬",
            "XX": "🌐",
        }
        return flag_map.get(country_code, "🌐")
