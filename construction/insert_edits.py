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
    parser.add_argument('--entity_str',
                        type=str,
                        nargs='+',
                        default=['human'])
    parser.add_argument('--QID',
                        type=str,
                        nargs='+',
                        default=['Q5'])
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

def main(args):
    with open(args.dataset_file_path, 'r+') as f:
        dataset = json.load(f)
    with open(args.exclusion_file_path, 'r') as f:
        exclusion_types = json.load(f)

    all_entities = []
    for case in dataset['edit']:
        triples = case['triples']['str']
        for key in triples.keys():
            for trip in triples[key]:
                all_entities.append(trip[0])
                if key in exclusion_types['str']:
                    all_entities.append(trip[2])
    all_entities = list(set(all_entities))

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
        LIMIT {len(dataset['edit'])*100 // len(args.QID)}
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
    item_counter = -1

    for case in tqdm(dataset['edit'], desc='Finding Edits'):
        rel_id = {rel['PID'] for rel in case['relations']}

        done_flag = False
        while not done_flag:
            item_counter += 1
            data = items[item_counter].get()
            if 'labels' not in data.keys():
                continue
            subj = data['labels'].get('en')
            if isinstance(subj, type(None)) or subj in all_entities:
                continue
            claims = {pid for pid in data['claims'].keys()}
            if 'human' in args.entity_str and not utils.has_appropriate_dob_dod(data, claims, year=1725):
                    continue
            edit_vectors = rel_id & claims
            if len(edit_vectors) < 1:
                continue
            description, _ = utils.has_long_enough_description(wikipedia_site, subj, data)
            if isinstance(description, type(None)):
                continue
            
            already_used = False
            all_objs = []
            str_triples = {}
            id_triples = {}

            for pid in edit_vectors:
                try:
                    prop = pywikibot.PropertyPage(wikidata_repo, pid)
                    prop.get()
                    rel = prop.labels.get('en')
                except:
                    continue

                edit_triples = []
                not_new = False
                for claim in data['claims'][pid]:
                    obj = utils.get_obj(claim)
                    if isinstance(obj, type(None)):
                        continue
                    elif obj in all_entities:
                        already_used = True
                        break 

                    for t in case['triples']['str'][rel]:
                        if obj == t[2]:
                            not_new = True
                            break
                    if not_new:
                        continue
                    
                    try:
                        obj_page = pywikibot.ItemPage(wikidata_repo, claim.target.title())
                        obj_page.get()

                        edit_triples.append({'str' : (case['entity']['str'], rel, obj), 
                                            'IDs' : (case['entity']['QID'], pid, claim.target.title()),
                                            'obj_aliases': obj_page.aliases.get('en')})
                    except:
                        continue
                    
                    if pid in exclusion_types['PID']:
                        all_objs.append(obj)

                if already_used:
                    break
                elif len(edit_triples) > 0:
                    str_triples[rel] = [trip['str'] for trip in edit_triples]
                    id_triples[pid] = [trip['IDs'] for trip in edit_triples]

            if len(list(str_triples.keys())) > 1:
                all_entities.append(subj)
                all_entities.extend(all_objs)
                dataset['edit'][case['case']]['edit_triples'] = {'mimicked_entity': {'str': subj,
                                                                                     'QID': items[item_counter].title()},
                                                                 'str': str_triples,
                                                                 'ID': id_triples}
                done_flag = True
                
    print('Dumping edits')
    json.dump(dataset, open(args.dataset_file_path, 'w'), indent=4)
    print('Done')

if __name__ == '__main__':
    random.seed(4096)

    args = parse_args()
    main(args)
