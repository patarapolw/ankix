import peewee as pv
from playhouse import sqlite_ext
from playhouse.shortcuts import model_to_dict

from datetime import datetime, timedelta
import random
import sys
import datauri
import re

from .config import config
from .jupyter import HTML

database = sqlite_ext.SqliteDatabase(config['database'])


class BaseModel(pv.Model):
    viewer_config = dict()

    @classmethod
    def get_viewer(cls, records):
        from htmlviewer import PagedViewer

        return PagedViewer([r.to_viewer() for r in records], **cls.viewer_config)

    class Meta:
        database = database


class Tag(BaseModel):
    name = pv.TextField(unique=True, collation='NOCASE')
    # notes

    def __repr__(self):
        return f'<Tag: "{self.name}">'

    def to_viewer(self):
        d = model_to_dict(self)
        d['notes'] = [repr(n) for n in self.notes]

        return d


class Media(BaseModel):
    name = pv.TextField(unique=True)
    data = pv.BlobField()
    # notes

    def __repr__(self):
        return f'<Media: "{self.name}">'

    @property
    def src(self):
        return datauri.build(bytes(self.data))

    @property
    def html(self):
        return f'<img src="{self.src}" />'

    def to_viewer(self):
        d = model_to_dict(self)
        d['data'] = self.html
        d['notes'] = [repr(n) for n in self.notes]

        return d

    viewer_config = {
        'renderer': {
            'data': 'html'
        },
        'colWidth': {
            'data': 600
        }
    }


class Model(BaseModel):
    name = pv.TextField(unique=True)
    css = pv.TextField()
    # templates

    def __repr__(self):
        return f'<Model: "{self.name}">'

    def to_viewer(self):
        d = model_to_dict(self)
        d['templates'] = [t.name for t in self.templates]

        return d


class Template(BaseModel):
    model = pv.ForeignKeyField(Model, backref='templates')
    name = pv.TextField()
    question = pv.TextField()
    answer = pv.TextField()

    class Meta:
        indexes = (
            (('model_id', 'name'), True),
        )

    def __repr__(self):
        return f'<Template: "{self.model.name}.{self.name}">'

    def to_viewer(self):
        d = model_to_dict(self)
        d['model'] = self.model.name
        d['cards'] = [repr(c) for c in self.cards]

        return d

    viewer_config = {
        'renderer': {
            'question': 'html',
            'answer': 'html'
        },
        'colWidth': {
            'question': 400,
            'answer': 400
        }
    }


class Deck(BaseModel):
    name = pv.TextField(unique=True)

    def __repr__(self):
        return f'<Deck: "{self.name}">'

    def to_viewer(self):
        d = model_to_dict(self)
        d['cards'] = [repr(c) for c in self.cards]

        return d


class Note(BaseModel):
    data = sqlite_ext.JSONField()
    medias = pv.ManyToManyField(Media, backref='notes', on_delete='cascade')
    tags = pv.ManyToManyField(Tag, backref='notes', on_delete='cascade')

    def mark(self, tag):
        Tag.get_or_create(name=tag)[0].notes.add(self)

    def unmark(self, tag):
        Tag.get_or_create(name=tag)[0].notes.remove(self)

    def to_viewer(self):
        d = model_to_dict(self)
        d['cards'] = '<br/>'.join(c.html for c in self.cards)
        d['tags'] = [t.name for t in self.tags]

        return d

    viewer_config = {
        'renderer': {
            'cards': 'html'
        },
        'colWidth': {
            'cards': 400
        }
    }


NoteTag = Note.tags.get_through_model()
NoteMedia = Note.medias.get_through_model()


class Card(BaseModel):
    note = pv.ForeignKeyField(Note, backref='cards')
    deck = pv.ForeignKeyField(Deck, backref='cards')
    template = pv.ForeignKeyField(Template, backref='cards')
    cloze_order = pv.IntegerField(null=True)
    srs_level = pv.IntegerField(null=True)
    next_review = pv.DateTimeField(null=True)

    def to_viewer(self):
        d = model_to_dict(self)
        d.update({
            'question': str(self.question),
            'answer': str(self.answer),
            'tags': [t.name for t in self.note.tags]
        })

        return d

    viewer_config = {
        'renderer': {
            'question': 'html',
            'answer': 'html'
        },
        'colWidth': {
            'question': 400,
            'answer': 400
        }
    }

    def _pre_render(self, html, is_question):
        for k, v in self.note.data.items():
            html = html.replace('{{%s}}' % k, v)
            html = html.replace('{{cloze:%s}}' % k, v)
            if self.cloze_order is not None:
                if is_question:
                    html = re.sub(r'{{c%d::([^}]+)}}' % self.cloze_order,
                                  '[...]', html)

                html = re.sub(r'{{c\d+::([^}]+)}}',
                              '\g<1>', html)

        return html

    @property
    def question(self):
        html = self._pre_render(self.template.question, is_question=True)

        return HTML(
            html,
            medias=self.note.medias,
            css=self.css
        )

    @property
    def answer(self):
        html = self._pre_render(self.template.answer, is_question=False)
        html = html.replace('{{FrontSide}}', self.question.raw)

        return HTML(
            html,
            medias=self.note.medias,
            css=self.css
        )

    @property
    def css(self):
        return self.template.model.css

    @property
    def html(self):
        return f'''
        <style>{self.css}</style>
        <div id='c{self.id}'>
            <br/>
            <div id='q{self.id}'>{self.question.raw}</div>
            <div id='a{self.id}' style='display: none;'>{self.answer.raw}</div>
        </div>

        <script>
        function toggleHidden(el){{
            if(el.style.display === 'none') el.style.display = 'block';
            else el.style.display = 'none';
        }}
        
        document.getElementById('c{self.id}').addEventListener('click', ()=>{{
            toggleHidden(document.getElementById('q{self.id}'));
            toggleHidden(document.getElementById('a{self.id}'));
        }})
        </script>
        '''

    def _repr_html_(self):
        return self.html

    def hide(self):
        return self.question

    def show(self):
        return self.answer

    def mark(self, name='marked'):
        self.note.mark(name)

    def unmark(self, name='marked'):
        self.note.unmark(name)

    def right(self):
        if not self.srs_level:
            self.srs_level = 1
        else:
            self.srs_level = self.srs_level + 1

        self.next_review = (datetime.now()
                            + config['srs'].get(int(self.srs_level), timedelta(weeks=4)))
        self.save()

    correct = next_srs = right

    def wrong(self, duration=timedelta(minutes=1)):
        if self.srs_level and self.srs_level > 1:
            self.srs_level = self.srs_level - 1

        self.bury(duration)

    incorrect = previous_srs = wrong

    def bury(self, duration=timedelta(hours=4)):
        self.next_review = datetime.now() + duration
        self.save()

    @classmethod
    def iter_quiz(cls, deck=None, tags=None):
        db_cards = list(cls.search(deck=deck, tags=tags))
        random.shuffle(db_cards)

        return iter(db_cards)

    iter_due = iter_quiz

    @classmethod
    def search(cls, deck=None, tags=None):
        query = cls.select()

        if deck:
            query = query.join(Deck).where(Deck.name == deck)

        if tags:
            query_params = (Tag.name == tags[0])
            for tag in tags[1:]:
                query_params = (query_params | (Tag.name == tag))

            query = query.join(Note).join(NoteTag).join(Tag).where(query_params)

        return query.order_by(cls.next_review.desc())


def create_all_tables():
    for cls in sys.modules[__name__].__dict__.values():
        if hasattr(cls, '__bases__') and issubclass(cls, pv.Model):
            if cls not in (BaseModel, pv.Model):
                cls.create_table()
