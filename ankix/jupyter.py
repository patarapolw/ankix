import mistune

from .util import is_html
from .config import config

markdown = mistune.Markdown()


class HTML:
    def __init__(self, html, css=''):
        if config['markdown'] or not is_html(html):
            self.raw = markdown(html)
        else:
            self.raw = html

        self.css = css

    def _repr_html_(self):
        return self.html

    def __repr__(self):
        return self.html

    def __str__(self):
        return self.html

    @property
    def html(self):
        return f'''
        <style>{self.css}</style>
        <br/>
        {self.raw}
        '''
