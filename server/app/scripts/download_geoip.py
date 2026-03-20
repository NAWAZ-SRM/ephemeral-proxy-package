import asyncio
import sys
import gzip
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.redis_client import get_redis, close_redis


MAXMind_URL = "https://download.maxmind.com/app/geoip_download"
DB_URL = f"{MAXMind_URL}?edition_id=GeoLite2-Country&license_key={settings.MAXMIND_LICENSE_KEY}&suffix=tar.gz"

DATA_DIR = Path(settings.GEOIP_DB_PATH).parent
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(settings.GEOIP_DB_PATH)


async def download_geoip():
    import httpx

    if not settings.MAXMIND_LICENSE_KEY:
        print("MAXMIND_LICENSE_KEY not set. Skipping GeoIP download.")
        print("Get a free license key at https://www.maxmind.com/en/geolite2/signup")
        return

    print(f"Downloading GeoLite2-Country database from MaxMind...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(DB_URL)
            if response.status_code != 200:
                print(f"Failed to download GeoIP DB: HTTP {response.status_code}")
                return

            tmp_tar = DATA_DIR / "GeoLite2-Country.tar.gz"
            tmp_tar.write_bytes(response.content())
            print("Download complete. Extracting...")

            import tarfile
            with tarfile.open(tmp_tar, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith(".mmdb"):
                        member.name = Path(member.name).name
                        tar.extract(member, DATA_DIR)

            extracted = next(DATA_DIR.glob("GeoLite2-Country*.mmdb"))
            if extracted.name != DB_PATH.name:
                extracted.rename(DB_PATH)
            else:
                shutil.copy2(extracted, DB_PATH)

            tmp_tar.unlink()
            for d in DATA_DIR.glob("GeoLite2-Country*"):
                if d.is_dir():
                    shutil.rmtree(d)

            print(f"GeoIP database installed at {DB_PATH}")
    except Exception as e:
        print(f"Error downloading GeoIP database: {e}")


if __name__ == "__main__":
    asyncio.run(download_geoip())
