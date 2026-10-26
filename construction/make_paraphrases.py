import json
import random
import argparse
from tqdm import tqdm

import pywikibot

from transformers import AutoModelForCausalLM, AutoTokenizer

import utils

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--num_paraphrases',
                        type=int,
                        default=3)
    parser.add_argument('--hf_model_path',
                        type=str,
                        default='meta-llama/Llama-3.1-8B-Instruct')
    parser.add_argument('--dataset_file_path',
                        type=str,
                        default='../datasets/dataset.json')
    parser.add_argument('--sentence_template_path',
                        type=str,
                        default='./sentence_templates.json')
    parser.add_argument('--hf_login_token',
                        type=str,
                        default='<YOUR_HF_TOKEN_HERE>')
    args = parser.parse_args()
    return args

def main(args):
    model = AutoModelForCausalLM.from_pretrained(args.hf_model_path, low_cpu_mem_usage=False, device_map='auto')
    tokenizer = AutoTokenizer.from_pretrained(args.hf_model_path, use_fast=False)
    tokenizer.pad_token = tokenizer.eos_token
    model.generation_config.pad_token_id = tokenizer.pad_token_id
    
    with open(args.dataset_file_path, 'r') as f:
        dataset = json.load(f)
    with open(args.sentence_template_path, 'r') as f:
        sentence_templates = json.load(f)
    
    used_QIDS = set()
    for case in dataset['edit']:
        used_QIDS.add(case['entity']['str'])
        used_QIDS.add(case['edit_triples']['mimicked_entity']['str'])
    
    site = pywikibot.Site('wikidata', 'wikidata')
    repo = site.data_repository()
    
    possible_qs = random.sample(range(1, 10000001), 10000000)
    q_count = 0

    for case in tqdm(dataset['edit'], desc='Generating Paraphrase Prompts'):
        for i, sentence_set in enumerate(case['edit_sentences']):
            templates = sentence_templates[sentence_set['relation']['PID']]
            individual_sentences = [temp.replace('SUBJ', sentence_set['subject']['str']).replace('OBJ', '') for temp in random.sample(templates, args.num_paraphrases)]
            
            for j in range(args.num_paraphrases):
                done_flag = False
                while not done_flag:
                    try:
                        item = pywikibot.ItemPage(site, f'Q{possible_qs[q_count]}')
                        item.get()
                        ent_name = item.labels.get('en')
                    except:
                        ent_name = None
                    if (not isinstance(ent_name, type(None))) and (ent_name not in used_QIDS):
                        input_promt = f'Give information about {ent_name}. Ensure the output is coherent and is less than 20 words.'
                        distractor = utils.model_generation(model, tokenizer, input_promt, max_new_tok=50, temperature=0.7)
                        distractor = ' '.join([val for val in distractor.split('\n') if val != ''])
                        if not "couldn't find any information" in distractor:
                            individual_sentences[j] = f'{distractor} {individual_sentences[j]}'
                            done_flag = True
                    q_count += 1
            
            dataset['edit'][case['case']]['edit_sentences'][i]['paraphrase_prompts'] = individual_sentences

    json.dump(dataset, open(args.dataset_file_path, 'w'), indent=4)            

if __name__ == '__main__':
    random.seed(6887)
    
    args = parse_args()

    from huggingface_hub import login
    login(args.hf_login_token)

    main(args)