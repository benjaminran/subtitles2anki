#!/usr/bin/env python3
import argparse
import dbm
import hashlib
import json
import logging

from google.cloud import translate_v2 as translate
from tqdm import tqdm
import genanki
import pysrt

#
# E.g.
# subtitles2anki.py --srt-in ~/Downloads/Sebastian.Fitzek\'s.Therapy.S01E02.Frantic.1080p.AMZN.WEB-DL.DD+5.1.H.264-playWEB.srt --anki-deck-name 'Therapy Ep. 2' --anki-out deck2.apkg --translations-cache cache-therapy.data
#

def hash(s):
    return int.from_bytes(hashlib.sha1(s.encode('utf-8')).digest(), 'big') % 2**32

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--srt-in')
    parser.add_argument('--stop-short', type=int)
    parser.add_argument('--anki-deck-name')
    parser.add_argument('--anki-deck-guid')
    parser.add_argument('--anki-out')
    parser.add_argument('--translations-cache')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.info(f'Running with args {args}')

    translate_client = translate.Client()

    anki_model = genanki.Model(
        1956853792,
        'Simple Model',
        fields=[
            {'name': 'Question'},
            {'name': 'Answer'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
            },
        ])

    deck = genanki.Deck(
        args.anki_deck_guid or hash(args.anki_deck_name),
        args.anki_deck_name)

    # open srt file, for each line translate it and add note to deck
    with dbm.open(args.translations_cache, 'c') as db:
        subs = pysrt.open(args.srt_in)
        sub_count = len(subs)
        for i, sub in tqdm(enumerate(subs), total=sub_count):
            if i == args.stop_short:
                break
            logging.debug('Got subtitle: %s', sub)
            heb = sub.text
            cache_lookup = db.get(heb, None)
            if cache_lookup is None:
                logging.debug('Cache miss, pulling from translate api...')
                translation_result = translate_client.translate(heb, target_language='en')
                db[heb] = json.dumps(translation_result)
            else:
                logging.debug('Cache hit: %s', cache_lookup)
                translation_result = json.loads(cache_lookup)
            logging.debug('Got translation_result %s', translation_result)
            en = translation_result['translatedText']
            note = genanki.Note(model=anki_model, fields=[heb, en])
            deck.add_note(note)
            logging.info('Added note %s / %s', heb, en)

    # write deck
    genanki.Package(deck).write_to_file(args.anki_out)
    logging.info('Wrote deck to file %s', args.anki_out)


if __name__ == '__main__':
    main()
