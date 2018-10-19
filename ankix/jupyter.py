import mistune

from .util import is_html, MediaType
from .config import config

markdown = mistune.Markdown()


class HTML:
    def __init__(self, html, media=None, model=None):
        if media is None:
            media = []

        self.media = media

        if config['markdown'] or not is_html(html):
            self._raw = markdown(html)
        else:
            self._raw = html

        self.model = model

    def _repr_html_(self):
        return self.html

    def __repr__(self):
        return self.html

    def __str__(self):
        return self.html

    @property
    def html(self):
        return f'''
        <style>{self.raw_css}</style>
        <br/>
        {self.raw}
        '''

    @property
    def raw(self):
        result = self._raw

        for medium in self.media:
            if medium.type_ == MediaType.audio:
                result = result.replace(f'[sound:{medium.name}]', medium.html)
            else:
                result = result.replace(medium.name, medium.src)

        return result

    @property
    def raw_css(self):
        css = '''
        div {
            display: block;
        }
        span {
            display: inline-block;
        }
        '''

        if self.model:
            css += self.model.css
            for font in self.model.fonts:
                css = css.replace(font.name, font.src)

        return css
