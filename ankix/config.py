from datetime import timedelta

from .util import parse_srs


class Config(dict):
    DEFAULT = {
        'database': '',
        'markdown': True,
        'srs': [
            timedelta(minutes=10),  # 0
            timedelta(hours=1),     # 1
            timedelta(hours=4),     # 2
            timedelta(hours=8),     # 3
            timedelta(days=1),      # 4
            timedelta(days=3),      # 5
            timedelta(weeks=1),     # 6
            timedelta(weeks=2),     # 7
            timedelta(weeks=4),     # 8
            timedelta(weeks=16)     # 9
        ]
    }

    def __init__(self):
        super(Config, self).__init__(**self.DEFAULT)

    def to_db(self):
        d = dict()
        for k, v in self.items():
            d[k] = {
                'srs': lambda x: parse_srs(x, self.DEFAULT['srs']),
            }.get(k, lambda x: x)(v)

        return d


config = Config()
