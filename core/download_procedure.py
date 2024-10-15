import json
import logging
import os
from pathlib import Path
import requests
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from core.classes import PodcastAndStorage, PodcastData
from core.constants import HISTORY_PATH

logger = logging.getLogger(__name__)

def create_or_fetch_history() -> tuple[PodcastAndStorage]:
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r") as file:
            history_list = json.load(file)
        return tuple(PodcastAndStorage(i["title"], i["rss"], i["loc"]) for i in history_list)
    else:
        return tuple()

def write_history(history: tuple[PodcastAndStorage]):
    with open(HISTORY_PATH, "w") as file:
        file.write(json.dumps([i.to_serial() for i in history], indent=4))

def is_valid_url(url: str) -> bool:
    check = urlparse(url)
    return all((check.scheme, check.netloc))

def get_podcast_title(url: str) -> str:
    processed_xml = ET.fromstring(requests.get(url).content)
    return processed_xml.find('./channel/title').text

def extract_from_xml(raw_xml: bytes) -> tuple[str, list[PodcastData]]:
    processed_xml = ET.fromstring(raw_xml)
    result = list[PodcastData]()
    for element in processed_xml.findall('./channel/item'):
        date = element.find("pubDate")
        title = element.find("title")
        url = element.find("enclosure")
        if None not in (date, title, url):
            result.append(PodcastData(date, title, url))
    return processed_xml.find('./channel/title').text, result

def download_podcasts(podcasts: tuple[PodcastAndStorage], stop_signal: list[int]) -> int:
    for podcast in podcasts:
        if not is_valid_url(podcast.rss):
            logger.warning(f"{podcast.rss} is not a valid URL. Skipping...")
            continue
        rss_response = requests.get(podcast.rss)
        podcast.title, podcast.podcast_data = extract_from_xml(rss_response.content)
        logger.info(f"Found {len(podcast.podcast_data)} episodes from {podcast.rss}")
        for episode in podcast.podcast_data:
            if len(stop_signal) > 0:
                logger.info(f"Stopping downloads")
                return 1
            filename, download_url = episode.process_data()
            save_location = Path(f"{podcast.loc}\\{filename}")
            if not save_location.exists():
                if filename == "<>":
                    logger.warning(f"Skipping episode with unsupported file type for episode at {download_url}")
                    continue
                logger.info(f"Downloading {filename} from {download_url}")
                episode_response = requests.get(download_url)
                with open(save_location, "wb") as file:
                    file.write(episode_response.content)
    return 0
