import sqlite3
from zipfile import ZipFile
from tempfile import TemporaryDirectory
import json
from tqdm import tqdm
import os
import re
import logging
import magic

from .config import config
from .util import MediaType
from .migration import do_migrate
from . import db


class Ankix:
    def __init__(self, database, markdown=False, srs=None, **kwargs):
        config.update(markdown=markdown, srs=srs)
        db.database.init(database, **kwargs)
        self.database = db.database

        if not os.path.exists(database):
            db.create_all_tables()

        if db.Settings.get_or_none() is None:
            db.Settings().save()
        else:
            config.update(db.Settings.to_dict())

        self.tables = {
            'settings': db.Settings,
            'tag': db.Tag,
            'media': db.Media,
            'model': db.Model,
            'template': db.Template,
            'deck': db.Deck,
            'note': db.Note,
            'note_tag': db.NoteTag,
            'note_media': db.NoteMedia,
            'card': db.Card
        }

    def __getitem__(self, item):
        return self.tables[item]

    def __getattr__(self, item):
        return getattr(self['card'], item)

    def __iter__(self):
        return iter(self['card'].select())

    def __len__(self):
        return self['card'].select().count()

    @classmethod
    def from_apkg(cls, src_apkg, filename=None, skip_media=False, **kwargs):
        if not filename:
            filename = os.path.splitext(src_apkg)[0] + '.ankix'

        db_class = cls(filename, **kwargs)
        db_class.import_apkg(src_apkg=src_apkg, skip_media=skip_media)

        return db_class

    def import_apkg(self, src_apkg, skip_media=False):
        """

        :param src_apkg:
        :param bool|list skip_media:
        :return:
        """
        info = dict()

        with TemporaryDirectory() as temp_dir:
            with self.database.atomic():
                with ZipFile(src_apkg) as zf:
                    zf.extractall(temp_dir)

                conn = sqlite3.connect(os.path.join(temp_dir, 'collection.anki2'))
                conn.row_factory = sqlite3.Row

                try:
                    d = dict(conn.execute('''SELECT * FROM col LIMIT 1''').fetchone())
                    for model in tqdm(tuple(json.loads(d['models']).values()), desc='models'):
                        self['model'].create(
                            id=model['id'],
                            name=model['name'],
                            css=model['css']
                        )

                        info.setdefault('model', dict())[int(model['id'])] = model
                        for media_name in re.findall(r'url\([\'\"]((?!.*//)[^\'\"]+)[\'\"]\)', model['css']):
                            info.setdefault('media', dict())\
                                .setdefault(MediaType.font, dict())\
                                .setdefault(media_name, [])\
                                .append(model['id'])

                        for template in model['tmpls']:
                            db_template = self['template'].get_or_create(
                                model_id=model['id'],
                                name=template['name'],
                                question=template['qfmt'],
                                answer=template['afmt'],
                            )[0]

                            info.setdefault('template', dict())[db_template.id] = template

                    for deck in tqdm(tuple(json.loads(d['decks']).values()), desc='decks'):
                        self['deck'].create(
                            id=deck['id'],
                            name=deck['name']
                        )

                    c = conn.execute('''SELECT * FROM notes''')
                    for note in tqdm(c.fetchall(), desc='notes'):
                        info_model = info['model'][note['mid']]
                        header = [field['name'] for field in info_model['flds']]

                        db_note = self['note'].create(
                            id=note['id'],
                            model_id=note['mid'],
                            data=dict(zip(header, note['flds'].split('\u001f')))
                        )

                        for tag in set(t for t in note['tags'].split(' ') if t):
                            db_tag = self['tag'].get_or_create(
                                name=tag
                            )[0]

                            db_tag.notes.add(db_note)

                        info.setdefault('note', dict())[note['id']] = dict(note)

                        for media_name in re.findall(r'src=[\'\"]((?!.*//)[^\'\"]+)[\'\"]', note['flds']):
                            info.setdefault('media', dict())\
                                .setdefault(MediaType.image, dict())\
                                .setdefault(media_name, [])\
                                .append(note['id'])

                        for media_name in re.findall(r'\[sound:[^\]]+\]', note['flds']):
                            info.setdefault('media', dict()) \
                                .setdefault(MediaType.audio, dict()) \
                                .setdefault(media_name, []) \
                                .append(note['id'])

                    c = conn.execute('''SELECT * FROM cards''')
                    for card in tqdm(c.fetchall(), desc='cards'):
                        info_note = info['note'][card['nid']]
                        info_model = info['model'][info_note['mid']]
                        db_model = self['model'].get(id=info_model['id'])
                        db_template = db_model.templates[0]

                        if '{{cloze:' not in db_template.question:
                            db_template = db_model.templates[card['ord']]
                            self['card'].create(
                                id=card['id'],
                                note_id=card['nid'],
                                deck_id=card['did'],
                                template_id=db_template.id
                            )
                        else:
                            for db_template_n in db_model.templates:
                                self['card'].create(
                                    id=card['id'],
                                    note_id=card['nid'],
                                    deck_id=card['did'],
                                    cloze_order=card['ord'] + 1,
                                    template_id=db_template_n.id
                                )

                    for db_deck in self['deck'].select():
                        if not db_deck.cards:
                            db_deck.delete_instance()
                finally:
                    conn.close()

                if not skip_media:
                    if skip_media is False:
                        skip_media = []

                    with open(os.path.join(temp_dir, 'media')) as f:
                        info_media = info.get('media', dict())
                        for media_id, media_name in tqdm(json.load(f).items(), desc='media'):
                            with open(os.path.join(temp_dir, media_id), 'rb') as image_f:
                                db_media = self['media'].create(
                                    id=int(media_id),
                                    name=media_name,
                                    data=image_f.read()
                                )

                                if MediaType.image not in skip_media:
                                    for note_id in info_media.get(MediaType.image, dict()).get(media_name, []):
                                        db_media.notes.add(self['note'].get(id=note_id))

                                if MediaType.audio not in skip_media:
                                    for note_id in info_media.get(MediaType.audio, dict()).get(media_name, []):
                                        db_media.notes.add(self['note'].get(id=note_id))

                                if MediaType.font not in skip_media:
                                    for model_id in info_media.get(MediaType.font, dict()).get(media_name, []):
                                        db_media.models.add(self['model'].get(id=model_id))

                                if not db_media.notes and db_media.models:
                                    logging.error('%s not connected to Notes or Models. Deleting...', media_name)
                                    db_media.delete_instance()

    def migrate(self, src_version, dst_version):
        do_migrate(src_version, dst_version)

    def add_model(self, model_name, templates: list, css=''):
        with self.database.atomic():
            db_model = self['model'].create(name=model_name, css=css)
            for template in templates:
                self['template'].create(
                    model_id=db_model.id,
                    **template
                )

        return db_model

    def get_models(self, model_name):
        db_query = self['model'].select()\
            .where(self['model'].name.contains(model_name))

        return db_query

    def add_note(self, note_data, model, card_to_decks: list, media_list: list=None):
        with self.database.atomic():
            if isinstance(model, int) or model.isdigit():
                db_model = self['model'].get(id=int(model))
            else:
                db_model = self['model'].get(name=model)

            db_note = self['note'].create(
                data=note_data,
                model_id=db_model.id
            )

            for deck, template in card_to_decks:
                if isinstance(deck, int) or deck.isdigit():
                    db_deck = self['deck'].get(id=int(deck))
                else:
                    db_deck = self['deck'].get_or_create(name=deck)[0]

                if isinstance(template, int) or template.isdigit():
                    db_template = self['template'].get(id=int(template))
                else:
                    db_template = self['template'].get(name=template)

                self['card'].create(
                    note_id=db_note.id,
                    deck_id=db_deck.di,
                    template_id=db_template.id
                )

            for media_name, media_path in media_list:
                type_ = {
                    'audio': MediaType.audio,
                    'font': MediaType.font
                }.get(magic.from_file(media_path, mime=True).split('/')[0], MediaType.image)

                with open(media_path, 'rb') as f:
                    self['media'].create(
                        name=media_name,
                        data=f.read(),
                        type_=type_
                    )

        return db_note

    def get_notes(self, model_name=None, deck_name=None, **note_data):
        db_query = self['note'].select()
        db_query = self._get_notes_query(db_query, model_name=model_name, deck_name=deck_name, **note_data)

        return db_query

    def _get_notes_query(self, db_query, model_name=None, deck_name=None, **note_data):
        for k, v in note_data:
            db_query = db_query.where(self['note'].data[k].contains(v))
        if model_name:
            db_query = db_query\
                .join(self['model'])\
                .where(self['model'].name.contains(model_name))
        if deck_name:
            db_query = db_query\
                .join(self['card']).join(self['deck'])\
                .where(self['deck'].name.contains(deck_name))

        return db_query

    def add_template(self, model_name, template_name, question, answer):
        db_model = self['model'].get(name=model_name)
        db_template = self['template'].create(
            model_id=db_model.id,
            name=template_name,
            question=question,
            answer=answer
        )

        return db_template

    def get_templates(self, model_name=None, template_name=None, question=None, answer=None):
        db_query = self['template'].select()
        if model_name:
            db_query = db_query.join(self['model']).where(self['model'].name.contains(model_name))
        if template_name:
            db_query = db_query.where(self['template'].name.contains(template_name))
        if question:
            db_query = db_query.where(self['template'].question.contains(question))
        if answer:
            db_query = db_query.where(self['template'].answer.contains(answer))

        return db_query

    def add_card(self, note_id, template_id, deck_name):
        db_deck = self['deck'].get(name=deck_name)
        db_card = self['card'].create(
            note_id=note_id,
            template_id=template_id,
            deck_id=db_deck.id
        )

        return db_card

    def get_cards(self, template_name=None, model_name=None, deck_name=None, **note_data):
        db_query = self['card'].select()
        if template_name:
            db_query = db_query.join(self['template']).where(self['template'].name.contains(template_name))
        if note_data:
            db_query = db_query.join(self['card'])
            db_query = self._get_notes_query(db_query, model_name=model_name, deck_name=deck_name, **note_data)

        return db_query
