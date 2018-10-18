from zipfile import ZipFile

if __name__ == '__main__':
    with ZipFile('/Users/patarapolw/Google Drive/Zanki Physiology and Pathology .apkg') as zf:
        zf.extractall('.')
