# Ankix

[![PyPI version shields.io](https://img.shields.io/pypi/v/ankix.svg)](https://pypi.python.org/pypi/ankix/)
[![PyPI license](https://img.shields.io/pypi/l/ankix.svg)](https://pypi.python.org/pypi/ankix/)

New file format for Anki with improved review intervals. Pure [peewee](https://github.com/coleifer/peewee) SQLite database, no zipfile. Available to work with on Jupyter Notebook.

## Usage

On Jupyter Notebook,

```python
>>> from ankix import Ankix
>>> db = Ankix.from_apkg('test.apkg', 'test.ankix')  # A file named 'test.ankix' will be created.
>>> # Or, db = Ankix('test.ankix')
>>> iter_quiz = db.iter_quiz()
>>> card = next(iter_quiz)
>>> card
'A flashcard is show on Jupyter Notebook. You can click to change card side, to answer-side.'
'It is HTML, CSS, Javascript, Image enabled. Cloze test is also enabled. Audio is not yet tested.'
>>> card.right()  # Mark the card as right
>>> card.wrong()  # Mark the card as wrong
>>> card.mark()  # Add the tag 'marked' to the note.
```

To view the internal working mechanism, and make use of Peewee capabilities,

```python
>>> db.tables
{'tag': <Model: Tag>,
 'media': <Model: Media>,
 'model': <Model: Model>,
 'template': <Model: Template>,
 'deck': <Model: Deck>,
 'note': <Model: Note>,
 'card': <Model: Card>}
 >>> db['card'].select().join(db['note']).where(db['note'].data['field_a'] == 'bar')[0]
 'The front side of the card is shown.'
```

## Installation

```commandline
$ pip install ankix
```

## Plans

- Add support for audio.
- Test by using it a lot.
