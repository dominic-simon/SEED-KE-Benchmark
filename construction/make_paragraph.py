import json
import random
import argparse
from tqdm import tqdm

from transformers import AutoModelForCausalLM, AutoTokenizer

import utils

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--slice_size',
                        type=int,
                        default=3)
    parser.add_argument('--split',
                        type=str,
                        default='edit',
                        choices=['edit', 'clean'])
    parser.add_argument('--hf_model_path',
                        type=str,
                        default='meta-llama/Llama-3.1-8B-Instruct')
    parser.add_argument('--dataset_file_path',
                        type=str,
                        default='../datasets/dataset.json')
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

    for case in tqdm(dataset[args.split], desc='Generating baseline paragraphs'):
        triples = []
        triples_str = []
        triples_QID = []

        qids = list(case['triples']['ID'].keys())
        strs = list(case['triples']['str'].keys())
        for i in range(len(strs)):
            random_val = random.choice(list(range(0, len(case['triples']['str'][strs[i]]))))
            trip = case['triples']['str'][strs[i]][random_val]
            triples_str.append(trip)
            triples_QID.append(case['triples']['ID'][qids[i]][random_val])
            trip = f"({', '.join(trip)})"
            triples.append(trip)

        iters = len(triples) // args.slice_size
        if (len(triples) % args.slice_size) > 0:
            iters += 1

        combined_paragraph = ''
        for j in tqdm(range(iters), desc=f'{case['case']+1}'):
            prompt = f"Provide information about {case['entity']['str']}. Make the response seem slightly natural." \
                     f"In the response, only include the information from the following relational triples as a single sentence each:\n{'\n'.join(triples[j*args.slice_size:(j+1)*args.slice_size])}"
            generated_text = utils.model_generation(model, tokenizer, prompt, temperature=0.4)
            generated_text = ' '.join([gt for gt in generated_text.split('\n') if gt != ''])
            for current_trip in triples[j*args.slice_size:(j+1)*args.slice_size]:
                if current_trip[2] not in generated_text:
                    generated_text = []
                    for single_trip in triples:
                        prompt = f"Translate the following relational triple into a sentence: {single_trip}"
                        gen = utils.model_generation(model, tokenizer, prompt, temperature=0.4)
                        generated_text.append(gen)
                    generated_text = ' '.join([gt.replace('\n', ' ') for gt in generated_text if gt != ''])
                    break
            generated_text = generated_text.replace('  ', ' ')
                    

            combined_paragraph = f'{combined_paragraph} {generated_text}'

        dataset[args.split][case['case']]['eval_paragraph'] = {'paragraph': combined_paragraph,
                                                               'used_triples': {'str': triples_str,
                                                                                'QID': triples_QID}}
    
    json.dump(dataset, open(args.dataset_file_path, 'w'), indent=4)

if __name__ == '__main__':
    random.seed(6887)

    args = parse_args()

    from huggingface_hub import login
    login(args.hf_login_token)

    main(args)