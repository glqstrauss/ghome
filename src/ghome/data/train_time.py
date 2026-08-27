import asyncio
import math
import time
from dataclasses import dataclass
from datetime import datetime

import niquests

from ghome.gen import gtfs_realtime_pb as gtfs
from ghome.logging_config import get_logger

FEEDS = ("nqrw", "bdfm", "ace")
FEED_URLS = [
    "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-" + feed
    for feed in FEEDS
]

_cache: dict[str, gtfs.FeedMessage] = {}

log = get_logger("train_time")


@dataclass
class Departure:
    line: str
    minutes: int


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
    return list(await asyncio.gather(*(get_feed(url) for url in FEED_URLS)))


def get_departure_times_for_stop(
    feeds: list[gtfs.FeedMessage], stop_id: str
) -> list[Departure]:
    now = datetime.now()
    departures: list[Departure] = []
    entities = (e for feed in feeds for e in feed.entity)
    updates = (e.trip_update for e in entities if e.trip_update is not None)

    for trip_update in updates:
        if trip_update.trip is None:
            continue
        for stop_time_update in trip_update.stop_time_update:
            if stop_time_update.stop_id != stop_id:
                continue
            route_id = trip_update.trip.route_id
            if route_id is None:
                break
            if (arrival := stop_time_update.arrival) is not None:
                minutes = math.ceil(
                    (datetime.fromtimestamp(arrival.time) - now).total_seconds() / 60
                )
                if minutes >= 0:
                    departures.append(Departure(route_id, minutes))
            break  # each trip visits a stop at most once

    return sorted(departures, key=lambda d: d.minutes)


if __name__ == "__main__":
    feeds = asyncio.run(get_feeds())
    departures = get_departure_times_for_stop(feeds, "R32N")
    if not departures:
        print("No upcoming departures found for stop R32N.")
    else:
        for dep in departures[:5]:
            print(f"{dep.line} {dep.minutes} min")
