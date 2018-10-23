import re
import json
from datetime import timedelta
from pytimeparse.timeparse import timeparse
import mistune

markdown = mistune.Markdown()
RE_IS_HTML = re.compile(r"(?:</[^<]+>)|(?:<[^<]+/>)")


def is_html(s):
    return RE_IS_HTML.search(s) is not None


class MediaType:
    image = 'image'
    font = 'font'
    audio = 'audio'


def timedelta2str(x):
    if isinstance(x, str):
        x = timedelta(seconds=timeparse(x))

    return str(x)


def parse_srs(value, default):
    if isinstance(value, (list, tuple, dict)):
        if isinstance(value, dict):
            d = default
            for k, v in value.items():
                d[int(k)] = v

            value = d
    else:
        raise ValueError

    return json.dumps([timedelta2str(x) for x in value])


def do_markdown(s):
    from .config import config
    if config.get('markdown'):
        return markdown(s)

    return s
