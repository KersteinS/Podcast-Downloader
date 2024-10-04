from datetime import datetime
import logging
import xml.etree.ElementTree as ET

from core.constants import SUPPORTED_AUDIO_FORMATS, SUPPORTED_DATE_FORMATS

logger = logging.getLogger(__name__)

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

    def interpret_date_data(self) -> datetime:
        """Add a pull request to support other date formats"""
        for i, date_format in enumerate(SUPPORTED_DATE_FORMATS):
            try:
                return datetime.strptime(self.date.text, date_format)
            except ValueError as e:
                if i == len(SUPPORTED_DATE_FORMATS)-1: # if this is the last attempt
                    raise ValueError(e)

    def clean_string(self) -> str:
        return "".join([i for i in self.title.text if i not in "\\/:*?\"<>|"]).rstrip()

    def determine_file_type(self) -> str:
        """Add a pull request to support other file audio types"""
        for audio_format in SUPPORTED_AUDIO_FORMATS:
            if audio_format in self.url.attrib['url']:
                return audio_format
        return ""

    def process_data(self) -> tuple[str]:
        """returns a tuple of a filename and url"""
        parsed_time = self.interpret_date_data().strftime("%Y-%m-%d")
        cleaned_title = self.clean_string()
        file_type = self.determine_file_type()
        if file_type == "":
            return ("<>", self.url.attrib['url'])
        return (f"{parsed_time} {cleaned_title}{file_type}", self.url.attrib['url'])

class PodcastAndStorage:
    """rss property is the URL to the podcast RSS feed. loc property is the file path to where the podcast files should be saved."""
    podcast_data: list[PodcastData]

    def __init__(self, rss: str, loc: str) -> None:
        self.rss = rss
        self.loc = loc

    def __repr__(self) -> str:
        return f"PodcastAndStorage({self.rss=} {self.loc=})"
