import json
import logging
import os
from pathlib import Path
import requests
import xml.etree.ElementTree as ET
from core.classes import PodcastAndStorage, PodcastData
from core.constants import HISTORY_PATH

logger = logging.getLogger(__name__)

def create_or_fetch_history() -> tuple[PodcastAndStorage]:
    if os.path.exists(HISTORY_PATH):
        history_list = json.load(open(HISTORY_PATH, "r"))
        return tuple(PodcastAndStorage(i[0],i[1]) for i in history_list)
    else:
        return tuple()

def generate_list_from_xml(raw_xml: bytes) -> list[PodcastData]:
    result = list[PodcastData]()
    processed_xml = ET.fromstring(raw_xml)
    for element in processed_xml.findall('./channel/item'):
        date = element.find("pubDate")
        title = element.find("title")
        url = element.find("enclosure")
        if None not in (date, title, url):
            result.append(PodcastData(date, title, url))
    return result

def download_podcasts(podcasts: tuple[PodcastAndStorage]):
    for podcast in podcasts:
        rss_response = requests.get(podcast.rss)
        podcast.podcast_data = generate_list_from_xml(rss_response.content)
        logger.info(f"Found {len(podcast.podcast_data)} episodes from {podcast.rss}")
        for episode in podcast.podcast_data:
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
