import json
import argparse
from tqdm import tqdm

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_file_path',
                        type=str,
                        default='../datasets/dataset.json')
    args = parser.parse_args()
    return args

def format_triple_dict(case, is_edit=False):
    if is_edit: 
        triples_str = []
        triples_id = []
        for es in case['edit_sentences']:
            triples_str.append((es['subject']['str'], es['relation']['str'], es['object']['str']))
            triples_id.append((es['subject']['QID'], es['relation']['PID'], es['object']['QID']))
    else:
        triples_str = case['eval_paragraph']['used_triples']['str']
        triples_id = case['eval_paragraph']['used_triples']['QID']

    str_id_pairs = []
    for i in range(len(triples_str)):
        sentence_template = None
        if is_edit:
            sentence_template = case['edit_sentences'][i]['template']
        else:
            for sentence_set in case['sentences']:
                if triples_str[i][1] == sentence_set['relation']['str'] and triples_str[i][2] == sentence_set['object']['str']:
                    sentence_template = sentence_set['template']
                    break

        str_id_pairs.append({'str': (triples_str[i][0], triples_str[i][1], triples_str[i][2]),
                             'ID': (triples_id[i][0], triples_id[i][1], triples_id[i][2]),
                             'sentence_template': sentence_template})

        if is_edit:
            str_id_pairs[i]['paraphrase_prompts'] = case['edit_sentences'][i]['paraphrase_prompts']

    return str_id_pairs

def main(args):
    with open(args.dataset_file_path, 'r') as f:
        dataset = json.load(f)
    updated_dataset = {'edit': [], 'clean': []}

    for split in tqdm(dataset.keys(), 'Cleaning Dataset Splits'):
        ds_split = dataset[split]
        for case in tqdm(ds_split, desc='Cleaning Individual Cases'):
            clean_str_id_pairs = format_triple_dict(case, is_edit=False)

            mimicked_entity = None
            edit_str_id_pairs = None
            if split == 'edit':
                edit_str_id_pairs = format_triple_dict(case, is_edit=True)
                mimicked_entity = {'str': case['edit_triples']['mimicked_entity']['str'],
                                   'QID': case['edit_triples']['mimicked_entity']['QID']}

            updated_dataset[split].append({'case': case['case'],
                                           'true_entity': {'str': case['entity']['str'],
                                                           'QID': case['entity']['QID'],
                                                           'aliases': case['aliases'],
                                                           'description': case['description']['wikidata']},
                                            'mimicked_entity': mimicked_entity,
                                            'triples': {'clean': clean_str_id_pairs,
                                                        'edits': edit_str_id_pairs},
                                            'reference_paragraph': case['eval_paragraph']['paragraph']})
    
    json.dump(updated_dataset, open(args.dataset_file_path, 'w'), indent=4)

if __name__ == '__main__':
    args = parse_args()
    main(args)