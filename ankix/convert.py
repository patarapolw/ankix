import sqlite3
from zipfile import ZipFile
from tempfile import TemporaryDirectory
import json
from tqdm import tqdm
import os
import re
import logging

from .config import config


def from_apkg(src_apkg, dst_ankix=None):
    if dst_ankix is None:
        dst_ankix = os.path.splitext(src_apkg)[0] + '.ankix'

    with TemporaryDirectory() as temp_dir:
        config['database'] = dst_ankix
        info = dict()

        from . import db
        # Tag Media Model Template Deck Note Card
        db.create_all_tables()

        with db.database.atomic():
            with ZipFile(src_apkg) as zf:
                zf.extractall(temp_dir)

            conn = sqlite3.connect(os.path.join(temp_dir, 'collection.anki2'))
            conn.row_factory = sqlite3.Row

            try:
                d = dict(conn.execute('''SELECT * FROM col LIMIT 1''').fetchone())
                for model in tqdm(tuple(json.loads(d['models']).values()), desc='models'):
                    db.Model.create(
                        id=model['id'],
                        name=model['name'],
                        css=model['css']
                    )

                    info.setdefault('model', dict())[model['id']] = model

                    for template in model['tmpls']:
                        db_template = db.Template.get_or_create(
                            model_id=model['id'],
                            name=template['name'],
                            question=template['qfmt'],
                            answer=template['afmt'],
                        )[0]

                        info.setdefault('template', dict())[db_template.id] = template

                for deck in tqdm(tuple(json.loads(d['decks']).values()), desc='decks'):
                    db.Deck.create(
                        id=deck['id'],
                        name=deck['name']
                    )

                c = conn.execute('''SELECT * FROM notes''')
                for note in tqdm(c.fetchall(), desc='notes'):
                    info_model = info['model'][note['mid']]
                    header = [field['name'] for field in info_model['flds']]

                    db_note = db.Note.create(
                        id=note['id'],
                        data=dict(zip(header, note['flds'].split('\u001f')))
                    )

                    for tag in set(t for t in note['tags'].split(' ') if t):
                        db_tag = db.Tag.get_or_create(
                            name=tag
                        )[0]

                        db_tag.notes.add(db_note)

                    info.setdefault('note', dict())[note['id']] = dict(note)

                    for media_name in re.findall(r'src=[\'\"]((?!//)[^\'\"]+)[\'\"]', note['flds']):
                        info.setdefault('media', dict()).setdefault(media_name, []).append(note['id'])

                c = conn.execute('''SELECT * FROM cards''')
                for card in tqdm(c.fetchall(), desc='cards'):
                    info_note = info['note'][card['nid']]
                    info_model = info['model'][info_note['mid']]
                    db_model = db.Model.get(id=info_model['id'])
                    db_template = db_model.templates[0]

                    if '{{cloze:' not in db_template.question:
                        db_template = db_model.templates[card['ord']]
                        db.Card.create(
                            id=card['id'],
                            note_id=card['nid'],
                            deck_id=card['did'],
                            template_id=db_template.id
                        )
                    else:
                        for db_template_n in db_model.templates:
                            db.Card.create(
                                id=card['id'],
                                note_id=card['nid'],
                                deck_id=card['did'],
                                cloze_order=card['ord']+1,
                                template_id=db_template_n.id
                            )

                for db_deck in db.Deck.select():
                    if not db_deck.cards:
                        db_deck.delete_instance()
            finally:
                conn.close()

            with open(os.path.join(temp_dir, 'media')) as f:
                info_media = info['media']
                for media_id, media_name in tqdm(json.load(f).items(), desc='medias'):
                    with open(os.path.join(temp_dir, media_id), 'rb') as image_f:
                        db_media = db.Media.create(
                            id=int(media_id),
                            name=media_name,
                            data=image_f.read()
                        )

                        for note_id in info_media.get(media_name, []):
                            db_media.notes.add(db.Note.get(id=note_id))

                        if not db_media.notes:
                            logging.error('%s not connected to Notes. Deleting...', media_name)
                            db_media.delete_instance()

    return dst_ankix
