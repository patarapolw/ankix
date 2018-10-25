from uuid import uuid4
import re

from .util import do_markdown


class TemplateMaker:
    def __init__(self, name, question, answer, css='', js='', _id=None):
        self.name = name
        self.question = do_markdown(question)
        self.answer = do_markdown(answer)
        self.css = css
        self.js = js
        self.sample = dict()

        if _id is None:
            self._id = str(uuid4())
        else:
            self._id = _id

    @property
    def html(self):
        raw = f'''
        <style>{self.css}</style>
        <div id='c{self._id}'>
            <br/>
            <div id='q{self._id}'>{self.question}</div>
            <div id='a{self._id}' style='display: none;'>{self.answer}</div>
        </div>

        <script>{self.js}</script>
        <script>
        function toggleHidden(el){{
            if(el.style.display === 'none') el.style.display = 'block';
            else el.style.display = 'none';
        }}

        document.getElementById('c{self._id}').addEventListener('click', ()=>{{
            toggleHidden(document.getElementById('q{self._id}'));
            toggleHidden(document.getElementById('a{self._id}'));
        }})
        </script>
        '''

        for k, v in self.sample.items():
            raw = raw.replace('{{%s}}' % k, do_markdown(str(v)))
            raw = raw.replace('{{cloze:%s}}' % k, do_markdown(str(v)))

        raw = re.sub('{{[^}]+}}', '', raw)

        return raw

    def _repr_html_(self):
        return self.html

    def __getitem__(self, item):
        return getattr(self, item)

    def get_sample(self, **kwargs):
        self.sample.update(kwargs)
