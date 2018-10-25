# Ankix

[![PyPI version shields.io](https://img.shields.io/pypi/v/ankix.svg)](https://pypi.python.org/pypi/ankix/)
[![PyPI license](https://img.shields.io/pypi/l/ankix.svg)](https://pypi.python.org/pypi/ankix/)

New file format for Anki with improved review intervals. Pure [peewee](https://github.com/coleifer/peewee) SQLite database, no zipfile. Available to work with on Jupyter Notebook.

## Usage

On Jupyter Notebook,

```python
>>> from ankix import ankix, db as a
>>> ankix.init('test.ankix')  # A file named 'test.ankix' will be created.
>>> ankix.import_apkg('foo.apkg')  # Import the contents from 'foo.apkg'
>>> iter_quiz = a.iter_quiz()
>>> card = next(iter_quiz)
>>> card
'A flashcard is show on Jupyter Notebook. You can click to change card side, to answer-side.'
'It is HTML, CSS, Javascript, Image enabled. Cloze test is also enabled. Audio is not yet tested.'
>>> card.right()  # Mark the card as right
>>> card.wrong()  # Mark the card as wrong
>>> card.mark()  # Add the tag 'marked' to the note.
```

You can directly make use of Peewee capabilities,

```python
 >>> a.Card.select().join(a.Note).where(a.Note.data['field_a'] == 'bar')[0]
 'The front side of the card is shown.'
```

## Adding new cards

Adding new cards is now possible. This has been tested in https://github.com/patarapolw/zhlib/blob/master/zhlib/export.py#L15

```python
from ankix import ankix, db as a
ankix.init('test.ankix')
a_model = a.Model.add(
    name='foo',
    templates=[
        a.TemplateMaker(
            name='Forward', 
            question=Q_FORMAT,
            answer=A_FORMAT
        ),
        a.TemplateMaker(
            name='Reverse', 
            question=Q_FORMAT,
            answer=A_FORMAT)
    ],
    css=CSS,
    js=JS
)
# Or, a_model = a.Model.get(name='foo')
for record in records:
    a.Note.add(
        data=record,
        model=a_model,
        card_to_decks={
            'Forward': 'Forward deck',
            'Reverse': 'Reverse deck'
        },
        tags=['bar', 'baz']
    )
```

## Installation

```commandline
$ pip install ankix
```

## Plans

- Test by using it a lot.
