import json
import random
import argparse
from tqdm import tqdm

import pywikibot
import mwparserfromhell
from pywikibot import pagegenerators

import utils

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--num_entities',
                        type=int,
                        default=5000)
    parser.add_argument('--property_str',
                        type=str,
                        nargs='+',
                        default=['human'])
    parser.add_argument('--property_ID',
                        type=str,
                        nargs='+',
                        default=['Q5'])
    parser.add_argument('--results_path',
                        type=str,
                        default='./results/relation_distribution.txt')
    args = parser.parse_args()
    
    for i in range(len(args.property_str)):
        args.property_str[i] = args.property_str[i].replace('_', ' ')

    return args

def main(args):
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    wikipedia_site = pywikibot.Site('en', 'wikipedia')

    query = f"""
             SELECT ?item WHERE {{
             VALUES ?class {{ {' '.join([f'wd:{pid}' for pid in args.property_ID])} }}
             ?item wdt:P31 ?class .
             }}
             LIMIT {args.num_entities*10}
             """
    generator = pagegenerators.WikidataSPARQLPageGenerator(query, site=wikidata_site)
    pbar = tqdm(total=args.num_entities, desc='Looking for Entities...')

    count = 0
    relations_seen = {}

    for item in generator:
        data = item.get()
        if 'labels' not in data.keys():
            continue
        subj = data['labels'].get('en')
        if isinstance(subj, type(None)):
            continue
        description, _ = utils.has_long_enough_description(wikipedia_site, subj, data)
        if isinstance(description, type(None)):
            continue
        entity_pids = list(data['claims'].keys())
        if ('human' in args.property_str) and (not utils.has_appropriate_dob_dod(data, entity_pids, year=1725)):
            continue
    
        for pid in entity_pids:
            page = pywikibot.PropertyPage(wikidata_site, pid)
            page.get()
            if page.type != 'wikibase-item':
                continue
            rel_str = page.labels.get('en')
            if not isinstance(rel_str, type(None)):
                if rel_str not in list(relations_seen.keys()):
                    relations_seen[rel_str] = 0
                relations_seen[rel_str] += 1

        pbar.update(1)
        count += 1
        if count >= args.num_entities:  
            pbar.close()
            break
    
    relations_seen = sorted(relations_seen.items(), key=lambda item: item[1], reverse=True)

    with open(args.results_path, 'w') as file:
        for rel, count in relations_seen:
            file.write(f'{rel}: {count}\n')

if __name__ == '__main__':
    args = parse_args()
    main(args)