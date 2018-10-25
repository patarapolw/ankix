import re
import json
from datetime import timedelta
from pytimeparse.timeparse import timeparse
import mistune
from pathlib import Path
import base64
import mimetypes

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


def build_base64(fp):
    """
    Build data URI according to RFC 2397
    (data:[<mediatype>][;base64],<data>)
    :param str|Path|bytes fp:
    :return:
    """
    if isinstance(fp, (str, Path)) and Path(fp).is_file():
        b = Path(fp).read_bytes()
        try:
            import magic
            mime = magic.from_file(fp, mime=True)
        except ImportError:
            mime, _ = mimetypes.guess_type(str(fp))
    else:
        import magic
        b = fp
        mime = magic.from_buffer(fp, mime=True)

    data64 = base64.b64encode(b).decode()

    return 'data:{};base64,{}'.format(mime, data64)

