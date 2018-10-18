from zipfile import ZipFile

if __name__ == '__main__':
    with ZipFile('/Users/patarapolw/Downloads/Chinese_Grammar_Wiki_Study_Deck.apkg') as zf:
        zf.extractall('.')
