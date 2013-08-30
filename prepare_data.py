#!/usr/bin/env python
# coding: utf-8

import sys
import os
import json
import time
from collections import defaultdict, OrderedDict
import xmltodict
import requests

DATA_DIR = 'data'

LANGUAGE_CODES_FILENAME = os.path.join(DATA_DIR, 'ISO-639-2_utf-8.txt')
LANGUAGE_CODES_JSON_FILENAME = os.path.join(DATA_DIR, 'lang_codes.json')

COUNTRY_CODES_FILENAME = os.path.join(DATA_DIR, 'country_codes.txt')
COUNTRY_CODES_JSON_FILENAME = os.path.join(DATA_DIR, 'country_codes.json')

SUPPLEMENTAL_DATA_FILENAME = os.path.join(DATA_DIR, 'supplementalData.xml')
LANG_TO_COUNTRY_INFO_JSON_FILENAME = os.path.join(DATA_DIR, 'lang_to_country_info.json')

LANG_TO_COUNTRY_NAMES = os.path.join(DATA_DIR, 'lang_to_country_names.json')

COUNTRY_TO_GEO_INFO_JSON_FILENAME = os.path.join(DATA_DIR, 'country_to_geo_info.json')

LANG_TO_COORDS_JSON_FILENAME = os.path.join(DATA_DIR, 'lang_to_coords.json')

def prepare_language_codes():
    lang_code_to_name = {}
    with open(LANGUAGE_CODES_FILENAME) as codes_file:
        for line in codes_file:
            alpha3bib, alpha3term, alpha2, eng, fr = map(lambda s: s.decode('utf-8').lower(), line.strip().split('|'))
            if alpha2 and eng:
                lang_code_to_name[alpha2] = eng
                # print alpha2, eng
    return lang_code_to_name


def prepare_country_codes():
    country_code_to_name = {}
    with open(COUNTRY_CODES_FILENAME) as codes_file:
        for line in codes_file:
            name, code = map(lambda s: s.decode('utf-8').lower(), line.strip().split(';'))
            if name and code:
                country_code_to_name[code] = name
                # print code, name
    return country_code_to_name

def prepare_lang_to_country_info():
    lang_to_country_info = defaultdict(list)
    with open(SUPPLEMENTAL_DATA_FILENAME) as data_file:
        data = xmltodict.parse(data_file.read())
        territories = data['supplementalData']['territoryInfo']['territory']

        for territory in territories:
            lang_populations = territory.get('languagePopulation', [])
            if isinstance(lang_populations, OrderedDict):
                lang_populations = [lang_populations]
            for lang_population in lang_populations:
                lang = lang_population['@type'].decode('utf-8').lower()
                country_info = {
                    'code': territory['@type'].decode('utf-8').lower(),
                    'population_percent': lang_population['@populationPercent'].decode('utf-8').lower(),
                    'official_status': lang_population.get('@officialStatus', '').decode('utf-8').lower()
                }

                lang_to_country_info[lang].append(country_info)
        
    return lang_to_country_info


def prepare_lang_country_names(country_code_to_name,
                               lang_to_country_info,
                               lang_code_to_name):
    lang_country_names = {}
    for lang, countries in lang_to_country_info.items():
        if len(lang) > 2:
            continue
        country_names = []
        for country_info in countries:
            country_code = country_info['code']
            country_name = country_code_to_name.get(country_code, 'undefined')
            official_status = country_info.get('official_status', '')
            if official_status.find('official') != -1:
                country_names.append(country_name.lower())
        lang_country_names[lang] = country_names
        # print lang, lang_code_to_name[lang], len(country_names), country_names
    return lang_country_names


def get_country_geo_info(country_name):
    time.sleep(0.5)
    url = 'http://maps.googleapis.com/maps/api/geocode/json'

    params = {
        'address': country_name.lower(),
        'sensor': 'false'
    }

    r = requests.get(url, params=params)
    print r.url
    assert r.status_code == 200
    results = r.json()['results']
    if not results:
        print >> sys.stderr, 'no info for ', country_name
        return {}

    first_result = results[0]
    geo_info = {}
    geo_info['geometry'] = first_result['geometry']
    geo_info['types'] = first_result['types']
    return geo_info


def prepare_lang_to_coords(lang_to_country_names, country_geo_info):
    lang_to_coords = {}

    for lang, country_names in lang_to_country_names.items():
        coords = []
        for name in country_names:
            geo_info = country_geo_info.get(name)
            if not geo_info:
                continue
            coords.append(geo_info['geometry']['location'])
        lang_to_coords[lang] = coords

    return lang_to_coords


def main():
    lang_code_to_name = prepare_language_codes()
    country_code_to_name = prepare_country_codes()
    lang_to_country_info = prepare_lang_to_country_info()

    lang_to_country_names = prepare_lang_country_names(country_code_to_name,
                                                       lang_to_country_info,
                                                       lang_code_to_name)

    with open(LANGUAGE_CODES_JSON_FILENAME, 'w') as json_file:
        json.dump(lang_code_to_name, json_file)

    with open(COUNTRY_CODES_JSON_FILENAME, 'w') as json_file:
        json.dump(country_code_to_name, json_file)

    with open(LANG_TO_COUNTRY_INFO_JSON_FILENAME, 'w') as json_file:
        json.dump(lang_to_country_info, json_file)

    with open(LANG_TO_COUNTRY_NAMES, 'w') as json_file:
        json.dump(lang_to_country_names, json_file)

    # country_names = country_code_to_name.values()
    # country_geo_info = dict((name, get_country_geo_info(name)) for name in country_names)

    # with open(COUNTRY_TO_GEO_INFO_JSON_FILENAME, 'w') as json_file:
    #     json.dump(country_geo_info, json_file)

    with open(COUNTRY_TO_GEO_INFO_JSON_FILENAME) as json_file:
        country_geo_info = json.load(json_file)

    lang_to_coords = prepare_lang_to_coords(lang_to_country_names, country_geo_info)

    with open(LANG_TO_COORDS_JSON_FILENAME, 'w') as json_file:
        json.dump(lang_to_coords, json_file)

    coord_to_langs = defaultdict(list)
    for lang, coords in lang_to_coords.items():
        for coord in coords:
            coord_to_langs[str(coord)].append(lang)

    for coord, langs in coord_to_langs.items():
        if len(langs) > 1:
            print 20 * '-'
            for lang in langs:
                print lang




if __name__ == '__main__':
    main()
