import peewee as pv
from playhouse.migrate import SqliteMigrator, migrate

from . import db


def do_migrate(src_version, dst_version, forced=False):
    migrator = SqliteMigrator(db.database)

    if (src_version, dst_version) == ('0.1.4', '0.1.5'):
        with db.database.atomic():
            for table_name in ['media', 'template', 'note', 'card']:
                try:
                    migrate(
                        migrator.add_column(table_name, 'h', pv.TextField(unique=True, null=True))
                    )
                except pv.OperationalError:
                    pass

            db.create_all_tables()

            for record in db.Media.select():
                try:
                    record.h = ''
                    record.save()
                except pv.IntegrityError:
                    print('{} is duplicated: {}'.format(record.id, record.name))
                    if not forced:
                        raise
                    else:
                        record.delete_instance()

            for record in db.Template.select():
                try:
                    record.h = ''
                    record.save()
                except pv.IntegrityError:
                    print('{} is duplicated: {}'.format(record.id, record.question + record.answer))
                    if not forced:
                        raise
                    else:
                        record.delete_instance()

            for record in db.Note.select():
                try:
                    data = record.data
                    for k, v in data.items():
                        record.data[k] = str(v)
                    record.save()
                except pv.IntegrityError:
                    print('{} is duplicated: {}'.format(record.id, record.data))
                    if not forced:
                        raise
                    else:
                        record.delete_instance()

            for record in db.Card.select():
                try:
                    record.h = ''
                    record.save()
                except pv.IntegrityError:
                    print('{} is duplicated: {}'.format(record.id, record.question.raw))
                    if not forced:
                        raise
                    else:
                        record.delete_instance()
    else:
        raise ValueError('Not supported for {}, {}'.format(src_version, dst_version))
