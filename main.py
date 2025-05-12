import asyncio
import aiohttp
import asyncpg
from models import Campground
from aiohttp import ClientError
import json
import time
from datetime import datetime
import logging

# Log ayarı
logging.basicConfig(
    filename="campground_errors.log",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


# ABD sınırları içinde kalan yaklaşık koordinatlar
min_lat, max_lat = 24, 50
min_lon, max_lon = -125, -66

# Tüm bbox'ları hazırla
bboxes = [
    f"{lon},{lat},{lon+1},{lat+1}"
    for lat in range(min_lat, max_lat)
    for lon in range(min_lon, max_lon)
]

API_URL_TEMPLATE = "https://thedyrt.com/api/v6/location-search-results?filter%5Bsearch%5D%5Bbbox%5D={}&page%5Bnumber%5D=1&page%5Bsize%5D=100&sort=recommended"

# Retry ayarları
MAX_RETRIES = 3
INITIAL_BACKOFF = 1

def parse_datetime(datetime_str):
    try:
        return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return None

async def fetch_bbox(session, bbox):
    url = API_URL_TEMPLATE.format(bbox)
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 30))
                    await asyncio.sleep(retry_after)
                elif 500 <= response.status < 600:
                    await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
                else:
                    msg = f"Non-retriable error {response.status} for bbox {bbox}"
                    print(msg)
                    logging.error(msg)
                    return []
        except (ClientError, asyncio.TimeoutError) as e:
            msg = f"Attempt {attempt+1}: error fetching bbox {bbox} - {e}"
            print(msg)
            logging.error(msg)
            await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
    return []

async def save_campgrounds(pool, campgrounds):
    async with pool.acquire() as conn:
        async with conn.transaction():
            for item in campgrounds:
                try:
                    attrs = item["attributes"]
                    # availability_updated_at'ı datetime formatına dönüştür
                    availability_updated_at = parse_datetime(attrs.get("availability-updated-at"))
                    
                    await conn.execute("""
                    INSERT INTO campgrounds (
                        id, type, name, latitude, longitude, region_name, administrative_area, nearest_city_name,
                        accommodation_type_names, bookable, camper_types, operator, photo_url, photo_urls,
                        photos_count, rating, reviews_count, slug, price_low, price_high, availability_updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8,
                        $9, $10, $11, $12, $13, $14,
                        $15, $16, $17, $18, $19, $20, $21
                    ) ON CONFLICT (id) DO UPDATE SET
                        type = EXCLUDED.type,
                        name = EXCLUDED.name,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        region_name = EXCLUDED.region_name,
                        administrative_area = EXCLUDED.administrative_area,
                        nearest_city_name = EXCLUDED.nearest_city_name,
                        accommodation_type_names = EXCLUDED.accommodation_type_names,
                        bookable = EXCLUDED.bookable,
                        camper_types = EXCLUDED.camper_types,
                        operator = EXCLUDED.operator,
                        photo_url = EXCLUDED.photo_url,
                        photo_urls = EXCLUDED.photo_urls,
                        photos_count = EXCLUDED.photos_count,
                        rating = EXCLUDED.rating,
                        reviews_count = EXCLUDED.reviews_count,
                        slug = EXCLUDED.slug,
                        price_low = EXCLUDED.price_low,
                        price_high = EXCLUDED.price_high,
                        availability_updated_at = EXCLUDED.availability_updated_at
                    """,
                    item["id"], item["type"], attrs["name"], attrs["latitude"], attrs["longitude"],
                    attrs.get("region-name"), attrs.get("administrative-area"), attrs.get("nearest-city-name"),
                    attrs.get("accommodation-type-names", []), attrs.get("bookable", False),
                    attrs.get("camper-types", []), attrs.get("operator"),
                    attrs.get("photo-url"), attrs.get("photo-urls", []), attrs.get("photos-count", 0),
                    attrs.get("rating"), attrs.get("reviews-count", 0), attrs.get("slug"),
                    float(attrs.get("price-low", 0.0)), float(attrs.get("price-high", 0.0)),
                    availability_updated_at
                    )
                except KeyError as e:
                    msg = f"Skipped due to missing key: {e}"
                    print(msg)
                    logging.error(msg)
                except Exception as e:
                    msg = f"DB insert error: {e} - item id: {item.get('id')}"
                    print(msg)
                    logging.error(msg)

async def main():
    connector = aiohttp.TCPConnector(limit=50)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        pool = await asyncpg.create_pool(
            host="localhost", database="case_study", user="user", password="password", port=5432
        )

        for i in range(0, len(bboxes), 20):
            chunk = bboxes[i:i+20]
            tasks = [fetch_bbox(session, bbox) for bbox in chunk]
            results = await asyncio.gather(*tasks)
            all_campgrounds = [item for sublist in results for item in sublist]
            await save_campgrounds(pool, all_campgrounds)
            print(f"Saved {len(all_campgrounds)} campgrounds from chunk {i // 20 + 1}")

        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
