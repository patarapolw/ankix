import mistune

from .util import is_html
from .config import config

markdown = mistune.Markdown()


class HTML:
    def __init__(self, html, css=''):
        if config['markdown'] or not is_html(html):
            self.html = markdown(html)
        else:
            self.html = html

        self.css = css

    def _repr_html_(self):
        return self.formatted

    def __repr__(self):
        return self.formatted

    def __str__(self):
        return self.formatted

    @property
    def formatted(self):
        return f'''
        <style>{self.css}</style>
        <br/>
        {self.html}
        '''
