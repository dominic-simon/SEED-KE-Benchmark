import os
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
    parser.add_argument('--entity_types',
                        type=str,
                        nargs='+',
                        default=['person'])
    parser.add_argument('--entity_str',
                        type=str,
                        nargs='+',
                        default='human')
    parser.add_argument('--QID',
                        type=str,
                        nargs='+',
                        default='Q5')
    parser.add_argument('--split',
                        type=str,
                        default='edit',
                        choices=['edit', 'clean'])
    parser.add_argument('--relation_file_path',
                        type=str,
                        default='./relations.json')
    parser.add_argument('--exclusion_file_path',
                        type=str,
                        default='./exclusion_properties.json')
    parser.add_argument('--dataset_file_path',
                        type=str,
                        default='../datasets/dataset.json')
    args = parser.parse_args()

    args.entity_str = args.entity_str[0].split(' ')
    for i in range(len(args.entity_str)):
        args.entity_str[i] = args.entity_str[i].replace('_', ' ')
    args.QID = args.QID[0].split(' ')
    
    return args

def get_select_relations(entity_types, data_path):
    with open(data_path, 'r') as f:
        everything = json.load(f)
    select = []
    for typing in entity_types:
        select.extend(everything[typing])
    relations = [rel['str'] for rel in select]
    pids = [rel['PID'] for rel in select]
    return relations, pids

def main(args):
    selected_relations, selected_pids = get_select_relations(args.entity_types, args.relation_file_path)

    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    wikidata_repo = wikidata_site.data_repository()
    wikipedia_site = pywikibot.Site('en', 'wikipedia')

    used_QIDS = set()
    items = []
    for qid in tqdm(args.QID, desc='Fetching Items'):
        query = f"""
        SELECT ?item WHERE {{
        VALUES ?class {{ {f'wd:{qid}'} }}
        ?item wdt:P31 ?class .
        }}
        LIMIT {int(args.num_entities / len(args.QID) * 10)}
        """ 
        flag = False
        while not flag:
            try:
                generator = pagegenerators.WikidataSPARQLPageGenerator(query, site=wikidata_site)
                flag = True
            except:
                pass
        for item in tqdm(generator, desc=qid):
            item.get()
            if item.title() not in used_QIDS:
                used_QIDS.add(item.title())
                items.append(item)
    random.shuffle(items)

    pbar = tqdm(total=args.num_entities, desc='Building Dataset')

    count = 0
    
    if os.path.exists(args.dataset_file_path):
        with open(args.dataset_file_path, 'r') as f:
            dataset = json.load(f)
        dataset[args.split] = []
        
        with open(args.exclusion_file_path, 'r') as f:
            exclusion_types = json.load(f)
        all_entities = []
        for case in dataset['clean' if args.split == 'edit' else 'edit']:
            all_entities = []
            for case in dataset['edit']:
                triples = case['triples']['str']
                for key in triples.keys():
                    for trip in triples[key]:
                        all_entities.append(trip[0])
                        if key in exclusion_types['str']:
                            all_entities.append(trip[2])
        all_entities = list(set(all_entities))
    else:
        dataset = {args.split: []}
        all_entities = []
        exclusion_types = {'str': [], 'PID': []}
    

    for item in items:
        data = item.get()
        if 'labels' not in data.keys():
            continue
        subj = data['labels'].get('en')
        if isinstance(subj, type(None)) or subj in all_entities:
            continue
        wikipedia_description, wikidata_description = utils.has_long_enough_description(wikipedia_site, subj, data)
        if isinstance(wikipedia_description, type(None)):
            continue
        elif 'thumb|' in wikipedia_description  or 'may refer to:' in wikipedia_description:
            continue
        entity_pids = list(data['claims'].keys())
        if ('human' in args.entity_str) and (not utils.has_appropriate_dob_dod(data, entity_pids, year=1725)):
            continue

        relations_used = []
        str_triples = {}
        id_triples = {}
        alias_triples = {}
        all_objs = []

        for pid in entity_pids:
            triples = []
            if pid in selected_pids:
                idx = selected_pids.index(pid)
                rel = selected_relations[idx]
                for claim in data['claims'][pid]:
                    obj = utils.get_obj(claim)
                    if isinstance(obj, type(None)):
                        continue
                    elif obj in all_entities:
                        continue
                    try:
                        obj_page = pywikibot.ItemPage(wikidata_repo, claim.target.title())
                        obj_page.get()
                        triples.append({'str' : (subj, rel, obj), 
                                        'IDs' : (item.title(), pid, claim.target.title()),
                                        'obj_aliases': obj_page.aliases.get('en')})
                    except:
                        continue
                    if pid in exclusion_types['PID']:
                        all_objs.append(obj)
                if len(triples) > 0:
                    relations_used.append({'str': rel, 'PID': pid})
                    str_triples[rel] = [trip['str'] for trip in triples]
                    id_triples[pid] = [trip['IDs'] for trip in triples]


        if len(relations_used) > 1:
            all_entities.append(subj)
            all_entities.extend(all_objs)
            dataset[args.split].append({'case': count, 
                                        'entity': {'str': subj,
                                                'QID': item.title()},
                                        'aliases': item.aliases.get('en'),
                                        'description': {'wikipedia': wikipedia_description,
                                                        'wikidata': wikidata_description},
                                        'relations': relations_used,
                                        'triples': {'str'  : str_triples,
                                                    'ID'   : id_triples}})
            pbar.update(1)
            count += 1

        if count >= args.num_entities: 
            pbar.close()
            break 
    
    json.dump(dataset, open(args.dataset_file_path, 'w'), indent=4)
                    
if __name__ == '__main__':
    args = parse_args()
    main(args)