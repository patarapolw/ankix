import peewee as pv
from playhouse import sqlite_ext
from datetime import datetime, timedelta
import random
import sys

from .config import config
from .jupyter import HTML

database = sqlite_ext.SqliteDatabase(config['database'])


class BaseModel(pv.Model):
    class Meta:
        database = database


class Tag(BaseModel):
    name = pv.TextField(unique=True, collation='NOCASE')


class Model(BaseModel):
    name = pv.TextField(unique=True)
    css = pv.TextField()


class Template(BaseModel):
    model = pv.ForeignKeyField(Model, backref='templates')
    name = pv.TextField(unique=False)
    question = pv.TextField()
    answer = pv.TextField()


class Deck(BaseModel):
    name = pv.TextField(unique=True)


class Note(BaseModel):
    data = sqlite_ext.JSONField()
    tags = pv.ManyToManyField(Tag, backref='notes', on_delete='cascade')

    def mark(self, tag):
        Tag.get_or_create(name=tag)[0].notes.add(self)

    def unmark(self, tag):
        Tag.get_or_create(name=tag)[0].notes.remove(self)


NoteTag = Note.tags.get_through_model()


class Card(BaseModel):
    note = pv.ForeignKeyField(Note, backref='cards')
    deck = pv.ForeignKeyField(Deck, backref='cards')
    template = pv.ForeignKeyField(Template, backref='cards')
    srs_level = pv.IntegerField(null=True)
    next_review = pv.DateTimeField(null=True)

    @property
    def front(self):
        return HTML(
            self.template.question.format().format(**self.note.data),
            css=self.css
        )

    @property
    def back(self):
        return HTML(
            self.template.answer.format().format(FrontSide=self.front, **self.note.data),
            css=self.css
        )

    @property
    def css(self):
        return self.template.model.css

    def _repr_html_(self):
        return self.front.formatted

    def hide(self):
        return self.front

    def show(self):
        return self.back

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
