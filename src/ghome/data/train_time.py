from gen import gtfs_realtime_pb as gtfs
import niquests
from datetime import datetime
import time
from logging_config import get_logger

FEEDS = ("nqrw", "bdfm", "ace")
FEED_URLS = [
    "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-" + feed
    for feed in FEEDS
]

_cache: dict[str, gtfs.FeedMessage] = {}

log = get_logger("train_time")


async def get_feed(url: str) -> gtfs.FeedMessage:
    global _cache

    feed = _cache.get(url)
    if (
        feed is not None
        and feed.header is not None
        and time.time() <= feed.header.timestamp + 30
    ):
        log.debug(f"Using cached feed for {url}")
        return feed

    resp = await niquests.aget(url)
    resp.raise_for_status()
    if not resp.content:
        raise ValueError("No content returned from the feed URL")
    feed = gtfs.FeedMessage.from_binary(resp.content)
    _cache[url] = feed
    log.debug(f"Cache updated for {url}")
    return feed


async def get_feeds() -> list[gtfs.FeedMessage]:
    feeds = await asyncio.gather(*(get_feed(url) for url in FEED_URLS))
    return feeds


def get_departure_times_for_stop(feeds: list[gtfs.FeedMessage], stop_id: str):
    departures: list[tuple[str, int]] = []
    entities = (e for feed in feeds for e in feed.entity)
    updates = (e.trip_update for e in entities if e.trip_update is not None)

    for trip_update in updates:
        if trip_update.trip is None:
            continue
        for stop_time_update in trip_update.stop_time_update:
            if (
                stop_time_update.stop_id == stop_id
                and (arrival := stop_time_update.arrival) is not None
            ):
                departures.append((trip_update.trip.route_id, arrival.time))
    return sorted(departures, key=lambda x: x[1])


if __name__ == "__main__":
    import asyncio

    feeds = asyncio.run(get_feeds())
    departures = get_departure_times_for_stop(feeds, "R32N")
    for departure in departures:
        departure_time = datetime.fromtimestamp(departure[1]).strftime("%I:%M %p")
        print(f"The next {departure[0]} train departs at {departure_time}")
