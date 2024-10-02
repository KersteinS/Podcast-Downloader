import json
import os
import requests
import string
import xml.etree.ElementTree as ET
from datetime import datetime

HISTORY_PATH = ".\\history.json"

def clean_string(text: str) -> str:
    return "".join([i for i in text if i not in "\\/:*?\"<>|"])


class PodcastData:
    """date property is the pubDate text from the rss element, title property is the title text from the rss element, url property is the attrib['url'] from the rss element"""

    def __init__(self, date: ET.Element, title: ET.Element, url: ET.Element) -> None:
        self.date = date
        self.title = title
        self.url = url

    def __repr__(self) -> str:
        return f"PodcastData({self.date.text=} {self.title.text=} {self.url.attrib['url']=})"

    def __str__(self) -> str:
        return f"{self.date} {self.title}"

    def procesed_data(self) -> tuple[str]:
        """returns a tuple of urls and filenames"""
        parsed_time = datetime.strptime(self.date.text, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d")
        cleaned_title = clean_string(self.title.text)
        return (f"{parsed_time} {cleaned_title}", self.url.attrib['url'])

class PodcastAndStorage:
    """rss property is the URL to the podcast RSS feed. loc property is the file path to where the podcast files should be saved."""
    podcast_data: list[PodcastData]

    def __init__(self, rss: str, loc: str) -> None:
        self.rss = rss
        self.loc = loc

    def __repr__(self) -> str:
        return f"PodcastAndStorage({self.rss=} {self.loc=})"

def create_or_fetch_history() -> tuple[tuple]:
    if os.path.exists(HISTORY_PATH):
        history_list = json.load(open(HISTORY_PATH, "r"))
        return tuple((PodcastAndStorage(i[0],i[1]) for i in history_list))
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
        response = requests.get(podcast.rss)
        podcast.podcast_data = generate_list_from_xml(response.content)
        print(*(i.procesed_data() for i in podcast.podcast_data), sep="\n")

def main():
    history = create_or_fetch_history()
    print(history)
    download_podcasts(history)

if __name__ == "__main__":
    main()