import mistune

from .util import is_html
from .config import config

markdown = mistune.Markdown()


class HTML:
    def __init__(self, html, medias=None, css=''):
        if medias is None:
            medias = []

        self.medias = medias

        if config['markdown'] or not is_html(html):
            self._raw = markdown(html)
        else:
            self._raw = html

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

    @property
    def raw(self):
        result = self._raw

        for image in self.medias:
            result = result.replace(image.name, image.src)

        return result
