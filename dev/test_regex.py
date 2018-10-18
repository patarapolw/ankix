import re
import json

if __name__ == '__main__':
    with open('sample.json') as f:
        print(re.findall(r'src=[\'\"]((?!//)[^\'\"]+)[\'\"]', json.load(f)['tables']['notes']['flds']))

    print(len(dict({
        'a': 1,
        'b': 2
    }).items()))
