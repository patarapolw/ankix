import re

RE_IS_HTML = re.compile(r"(?:</[^<]+>)|(?:<[^<]+/>)")


def is_html(s):
    return RE_IS_HTML.search(s) is not None
