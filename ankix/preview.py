from uuid import uuid4


class TemplateMaker:
    def __init__(self, question, answer, css='', _id=None):
        self.question = question
        self.answer = answer
        self.css = css

        if _id is None:
            self._id = str(uuid4())
        else:
            self._id = _id

    @property
    def html(self):
        return f'''
        <style>{self.css}</style>
        <div id='c{self._id}'>
            <br/>
            <div id='q{self._id}'>{self.question}</div>
            <div id='a{self._id}' style='display: none;'>{self.answer}</div>
        </div>

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

    def _repr_html_(self):
        return self.html

    def __getitem__(self, item):
        return getattr(self, item)
