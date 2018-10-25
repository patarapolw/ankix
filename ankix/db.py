import peewee as pv
from playhouse import sqlite_ext, signals
from playhouse.shortcuts import model_to_dict

from datetime import datetime, timedelta
from pytimeparse.timeparse import timeparse
import random
import sys
import re
import json
import hashlib
import magic

from .config import config
from .jupyter import HTML
from .util import MediaType, parse_srs, do_markdown, build_base64
from .preview import TemplateMaker

database = sqlite_ext.SqliteDatabase(None)


class BaseModel(signals.Model):
    viewer_config = dict()

    def to_viewer(self):
        return model_to_dict(self)

    @classmethod
    def get_viewer(cls, records):
        from htmlviewer import PagedViewer

        return PagedViewer([r.to_viewer() for r in records], **cls.viewer_config)

    class Meta:
        database = database


class Settings(BaseModel):
    DEFAULT = config.to_db()

    markdown = pv.BooleanField(default=DEFAULT['markdown'])
    _srs = pv.TextField(default=DEFAULT['srs'])

    @classmethod
    def to_dict(cls):
        db_settings = cls.get()
        d = model_to_dict(db_settings)
        d.pop('_srs')
        d['srs'] = db_settings.srs

        return d

    @property
    def srs(self):
        d = dict()
        for i, s in enumerate(json.loads(str(self._srs))):
            d[i] = timedelta(seconds=timeparse(s))

        return d

    @srs.setter
    def srs(self, value):
        self._srs = parse_srs(value, self.srs)
        self.save()


@signals.post_save(sender=Settings)
def auto_update_config(model_class, instance, created):
    config.update(model_class.to_dict())


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
    type_ = pv.TextField(default=MediaType.font)
    data = pv.BlobField()
    h = pv.TextField(unique=True)
    # models (for css)
    # notes

    def __repr__(self):
        return f'<Media: "{self.name}">'

    @property
    def src(self):
        return build_base64(bytes(self.data))

    @property
    def html(self):
        if self.type_ == MediaType.font:
            return f'<img src="{self.src}" />'
        elif self.type_ == MediaType.audio:
            return f'<audio controls src="{self.src}" />'
        else:
            return f'<pre>{repr(self)}</pre>'

    def to_viewer(self):
        d = model_to_dict(self)
        d['data'] = self.html
        d['models'] = [repr(m) for m in self.models]
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


@signals.pre_save(sender=Media)
def media_pre_save(model_class, instance, created):
    instance.h = hashlib.md5(instance.data).hexdigest()


class Model(BaseModel):
    name = pv.TextField(unique=True)
    css = pv.TextField(default='')
    js = pv.TextField(default='')
    fonts = pv.ManyToManyField(Media, backref='models')
    # templates

    @classmethod
    def clean(cls):
        i = 0
        for db_model in cls.select():
            if not db_model.templates:
                i += 1
                db_model.delete_instance()

        return i

    @classmethod
    def add(cls, name, templates, css='', js=''):
        """

        :param name:
        :param list templates: list of dict or list of TemplateMaker
        :param css:
        :param js:
        :return:
        """
        with database.atomic():
            db_model = cls.create(name=name, css=css, js=js)
            for template in templates:
                Template.create(
                    model_id=db_model.id,
                    name=template['name'],
                    question=template['question'],
                    answer=template['answer']
                )

        return db_model

    def __repr__(self):
        return f'<Model: "{self.name}">'

    def to_viewer(self):
        d = model_to_dict(self)
        d['fonts'] = [repr(f) for f in self.fonts]
        d['templates'] = [t.name for t in self.templates]

        return d


ModelFont = Model.fonts.get_through_model()


class Template(BaseModel):
    model = pv.ForeignKeyField(Model, backref='templates')
    name = pv.TextField()
    question = pv.TextField()
    answer = pv.TextField()
    h = pv.TextField(unique=True)

    class Meta:
        indexes = (
            (('model_id', 'name'), True),
        )

    @classmethod
    def add(cls, model_name, template_name, question, answer):
        db_model = Model.get(name=model_name)
        db_template = cls.create(
            model_id=db_model.id,
            name=template_name,
            question=question,
            answer=answer
        )

        return db_template

    @classmethod
    def get_by_name(cls, model_name, template_name):
        return cls.select().join(Model) \
            .where((cls.name == template_name) & (Model.name == model_name))[0]

    @classmethod
    def search(cls, model_name=None, template_name=None, question=None, answer=None):
        db_query = cls.select()
        if model_name:
            db_query = db_query.join(Model).where(Model.name.contains(model_name))
        if template_name:
            db_query = db_query.where(cls.name.contains(template_name))
        if question:
            db_query = db_query.where(cls.question.contains(question))
        if answer:
            db_query = db_query.where(cls.answer.contains(answer))

        return db_query

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

    @property
    def html(self):
        return TemplateMaker(
            name=self.name,
            question=self.question,
            answer=self.answer,
            css=self.model.css,
            js=self.model.js,
            _id=self.id
        ).html

    def _repr_html_(self):
        return self.html


@signals.pre_save(sender=Template)
def template_pre_save(model_class, instance, created):
    instance.h = hashlib.md5((instance.question + instance.answer).encode()).hexdigest()


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
    model = pv.ForeignKeyField(Model, backref='notes')
    media = pv.ManyToManyField(Media, backref='notes', on_delete='cascade')
    tags = pv.ManyToManyField(Tag, backref='notes', on_delete='cascade')
    h = pv.TextField(unique=True)

    def mark(self, tag):
        Tag.get_or_create(name=tag)[0].notes.add(self)

    def unmark(self, tag):
        Tag.get_or_create(name=tag)[0].notes.remove(self)

    def rename_field(self, old_name, new_name):
        for db_note in Note.select(Note.data, Note.model_id).where(model_id=self.model_id):
            if old_name in db_note.data.keys():
                db_note.data[new_name] = db_note.data.pop(old_name)
                db_note.save()

    @classmethod
    def add(cls, data, model, card_to_decks: dict, media: dict=None, tags: list=None):
        if media is None:
            media = dict()
        if tags is None:
            tags = list()

        with database.atomic():
            if isinstance(model, int) or (isinstance(model, str) and model.isdigit()):
                db_model = Model.get(id=int(model))
            elif isinstance(model, Model):
                db_model = model
            else:
                db_model = Model.get(name=model)

            db_note = cls.create(
                data=data,
                model_id=db_model.id
            )

            for template, deck in card_to_decks.items():
                if isinstance(deck, int) or (isinstance(deck, str) and deck.isdigit()):
                    db_deck = Deck.get(id=int(deck))
                elif isinstance(deck, Deck):
                    db_deck = deck
                else:
                    db_deck = Deck.get_or_create(name=deck)[0]

                if isinstance(template, int) or (isinstance(template, str) and template.isdigit()):
                    db_template = Template.get(id=int(template))
                elif isinstance(template, Template):
                    db_template = template
                else:
                    db_template = Template.get(model_id=db_model.id, name=template)

                Card.create(
                    note_id=db_note.id,
                    deck_id=db_deck.id,
                    template_id=db_template.id
                )

            for media_name, media_path in media.items():
                type_ = {
                    'audio': MediaType.audio,
                    'font': MediaType.font
                }.get(magic.from_file(media_path, mime=True).split('/')[0], MediaType.image)

                with open(media_path, 'rb') as f:
                    Media.create(
                        name=media_name,
                        data=f.read(),
                        type_=type_
                    )

            for tag_name in tags:
                Tag.get_or_create(name=tag_name)[0].notes.add(db_note)

        return db_note

    @classmethod
    def search(cls, model_name=None, deck_name=None, tags=None, data=None):
        db_query = cls.select()
        if deck_name:
            db_query = db_query \
                .join(Card).join(Deck) \
                .where(Deck.name.contains(deck_name))

        db_query = cls._build_query(db_query, model_name=model_name, tags=tags, data=data)

        return db_query

    @classmethod
    def _build_query(cls, db_query, model_name=None, tags=None, data=None):
        db_query = db_query.switch(cls)

        if data:
            for k, v in data.items():
                db_query = db_query.where(cls.data[k].contains(v))
        if model_name:
            db_query = db_query \
                .join(Model) \
                .where(Model.name.contains(model_name))
        if tags:
            db_query = db_query\
                .join(NoteTag).join(Tag)\
                .where(~Tag.name.not_in(tags))

        return db_query

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
NoteMedia = Note.media.get_through_model()


@signals.pre_save(sender=Note)
def note_pre_save(model_class, instance, created):
    d = dict()
    for k, v in instance.data.items():
        if v in {None, ''}:
            continue

        if isinstance(v, (str, int, float, bool)):
            d[k] = v
        else:
            raise ValueError('Field {} is not string: {}'.format(k, v))

    instance.data = d
    instance.h = hashlib.md5(json.dumps(d, sort_keys=True).encode()).hexdigest()


class Card(BaseModel):
    note = pv.ForeignKeyField(Note, backref='cards')
    deck = pv.ForeignKeyField(Deck, backref='cards')
    template = pv.ForeignKeyField(Template, backref='cards')
    cloze_order = pv.IntegerField(null=True)
    srs_level = pv.IntegerField(null=True)
    next_review = pv.DateTimeField(null=True)
    h = pv.TextField(unique=True)

    @property
    def css(self):
        return self.template.model.css

    @css.setter
    def css(self, value):
        db_model = self.template.model
        db_model.css = value
        db_model.save()

    @classmethod
    def add(cls, note_id, template_id, deck_name):
        db_deck = Deck.get(name=deck_name)
        db_card = cls.create(
            note_id=note_id,
            template_id=template_id,
            deck_id=db_deck.id
        )

        return db_card

    @classmethod
    def search(cls, template_name=None, model_name=None, deck_name=None, tags=None, note_data=Note):
        db_query = cls.select()
        if template_name:
            db_query = db_query.join(Template).where(Template.name.contains(template_name))
        if deck_name:
            db_query = db_query.switch(cls) \
                .join(Deck) \
                .where(Deck.name.contains(deck_name))
        if note_data:
            db_query = Note._build_query(db_query, model_name=model_name, tags=tags, data=note_data)

        return db_query

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
        def _sub(x):
            field_k, content = x.groups()
            if self.note.data[field_k]:
                return content
            else:
                return ''

        html = re.sub(r'{{#([^}]+)}}(.*){{/\1}}', _sub, html, flags=re.DOTALL)

        for k, v in self.note.data.items():
            html = html.replace('{{%s}}' % k, do_markdown(str(v)))
            html = html.replace('{{cloze:%s}}' % k, do_markdown(str(v)))
            if self.cloze_order is not None:
                if is_question:
                    html = re.sub(r'{{c%d::([^}]+)}}' % self.cloze_order,
                                  '[...]', html)

                html = re.sub(r'{{c\d+::([^}]+)}}',
                              '\g<1>', html)

        html = re.sub('{{[^}]+}}', '', html)

        return html

    @property
    def question(self):
        html = self._pre_render(self.template.question, is_question=True)

        return HTML(
            html,
            media=self.note.media,
            model=self.template.model
        )

    @property
    def answer(self):
        html = self._pre_render(self.template.answer, is_question=False)
        html = html.replace('{{FrontSide}}', self.question.raw)

        return HTML(
            html,
            media=self.note.media,
            model=self.template.model
        )

    @property
    def html(self):
        return TemplateMaker(
            name=self.template.name,
            question=self.question.raw,
            answer=self.answer.raw,
            css=self.question.raw_css,
            _id=self.id
        ).html

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
    def iter_quiz(cls, template_name=None, model_name=None, deck_name=None, tags=None):
        db_cards = list(cls.search(
            template_name=template_name,
            model_name=model_name,
            deck_name=deck_name,
            tags=tags
        ))
        random.shuffle(db_cards)

        return iter(db_cards)

    iter_due = iter_quiz


@signals.pre_save(sender=Card)
def card_pre_save(model_class, instance, created):
    instance.h = hashlib.md5(instance.question.raw.encode()).hexdigest()


def create_all_tables():
    for cls in sys.modules[__name__].__dict__.values():
        if hasattr(cls, '__bases__') and issubclass(cls, pv.Model):
            if cls not in {BaseModel, pv.Model, signals.Model}:
                cls.create_table()
