from .config import config
from .convert import from_apkg


class Ankix:
    def __init__(self, database, **kwargs):
        config.update({
            'database': database,
            **kwargs
        })

        from . import db
        # Tag Media Model Template Deck Note Card
        db.create_all_tables()

        self.tables = {
            'tag': db.Tag,
            'media': db.Media,
            'model': db.Model,
            'template': db.Template,
            'deck': db.Deck,
            'note': db.Note,
            'card': db.Card
        }

    @classmethod
    def from_apkg(cls, src_apkg, dst_ankix=None, **kwargs):
        return cls(from_apkg(src_apkg=src_apkg, dst_ankix=dst_ankix), **kwargs)

    def __getitem__(self, item):
        return self.tables[item]

    def __getattr__(self, item):
        return getattr(self.tables['card'], item)

    def __iter__(self):
        return iter(self.tables['card'].select())

    def __len__(self):
        return self.tables['card'].select().count()
