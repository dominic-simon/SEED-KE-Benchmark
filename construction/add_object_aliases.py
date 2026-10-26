import json
import argparse
import pywikibot
from tqdm import tqdm
from pywikibot import config

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_file_path',
                        type=str,
                        default='../datasets/dataset.json')
    args = parser.parse_args()
    return args

def get_aliases(objs, ref_obj_str):
    alias_list = []
    if not isinstance(objs, list):
        objs = [objs]
    for o in objs:
        o = o.getTarget()
        if not isinstance(o, type(None)):
            try:
                obj_name = o.labels.get('en')
            except:
                obj_name = None
            if not isinstance(obj_name, type(None)) and obj_name != ref_obj_str:
                alias_list.extend([obj_name])
            try:
              obj_aliases = o.aliases.get('en')
            except:
              obj_aliases = None
            if not isinstance(obj_aliases, type(None)):
                alias_list.extend(obj_aliases)
    return alias_list

def add_aliases(dataset_file_path):
    with open(dataset_file_path, 'r') as f:
        ds = json.load(f)

    site = pywikibot.Site('wikidata', 'wikidata')
    repo = site.data_repository()
    
    for split in ds.keys():
        for i in tqdm(range(len(ds[split])), desc=split):
            subj =  ds[split][i]['true_entity']
            subj_wiki = pywikibot.ItemPage(repo, subj['QID'])
            subj_wiki.get()
            for j in range(len(ds[split][i]['triples'])):
                rel = ds[split][i]['triples'][j]['relation']
                obj_true = ds[split][i]['triples'][j]['object_true']
                obj_new = ds[split][i]['triples'][j]['object_new']

                if rel['PID'] in subj_wiki.claims:
                    aliases_true = get_aliases(subj_wiki.claims[rel['PID']], obj_true['str'])
                else:
                    aliases_true = []
                ds[split][i]['triples'][j]['object_true']['aliases'] = aliases_true
                if not isinstance(obj_new['QID'], type(None)):
                    new_obj_wiki = pywikibot.ItemPage(repo, obj_new['QID'])
                    new_obj_wiki.get()
                    aliases_new = new_obj_wiki.aliases.get('en')
                    if not isinstance(aliases_new, type(None)):
                        if len(set(aliases_true) & set(aliases_new)) > 0 or obj_new['str'] in aliases_true or obj_true['str'] in aliases_new:
                            ds[split][i]['triples'][j]['object_new']['str'] = None
                            ds[split][i]['triples'][j]['object_new']['QID'] = None
                            ds[split][i]['triples'][j]['paraphrase_prompts'] = None
                            ds[split][i]['triples'][j]['object_new']['aliases'] = []
                        else:
                            ds[split][i]['triples'][j]['object_new']['aliases'] = aliases_new
                    else:
                        ds[split][i]['triples'][j]['object_new']['aliases'] = []
    
    json.dump(ds, open(dataset_file_path, 'w'), indent=4)


if __name__ == '__main__':
    config.max_requests_per_minute = 30
    config.retry_wait = 5
    config.retry_max = 25

    args = parse_args()
    add_aliases(args.dataset_file_path)