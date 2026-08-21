import requests
from src.gen import gtfs_realtime_pb as gtfs_rt
from src.gen import gtfs_realtime_NYCT_pb
FEED_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw"

def main():
    resp = requests.get(FEED_URL)
    resp.raise_for_status()

    feed = gtfs_rt.FeedMessage.from_binary(resp.content)

    with open("feed.json", "w") as f:
        f.write(feed.to_json())


if __name__ == "__main__":
    main()
