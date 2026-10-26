import json
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_file_path',
                        type=str,
                        default='../datasets/dataset.json')
    args = parser.parse_args()
    return args

def main(args):
    with open(args.dataset_file_path, 'r') as f:
        dataset = json.load(f)
    for split in dataset.keys():
        for i in range(len(dataset[split])):
            new_triples = []
            for j in range(len(dataset[split][i]['triples']['clean'])):
                subj_str = dataset[split][i]['triples']['clean'][j]['str'][0]
                subj_qid = dataset[split][i]['triples']['clean'][j]['ID'][0]
                rel_str = dataset[split][i]['triples']['clean'][j]['str'][1]
                rel_pid = dataset[split][i]['triples']['clean'][j]['ID'][1]
                obj_true_str = dataset[split][i]['triples']['clean'][j]['str'][2]
                obj_true_qid = dataset[split][i]['triples']['clean'][j]['ID'][2]
                obj_edit_str = None
                obj_edit_qid = None
                sentence_template = dataset[split][i]['triples']['clean'][j]['sentence_template']
                paraphrase_prompts = None
                if split == 'edit':
                        for k in range(len(dataset[split][i]['triples']['edits'])):
                            if rel_str == dataset[split][i]['triples']['edits'][k]['str'][1]:
                                obj_edit_str = dataset[split][i]['triples']['edits'][k]['str'][2]
                                obj_edit_qid = dataset[split][i]['triples']['edits'][k]['ID'][2]
                                paraphrase_prompts = dataset[split][i]['triples']['edits'][k]['paraphrase_prompts']
                                break
                edit_triples = {'subject': {'str': subj_str,
                                            'QID': subj_qid},
                                'relation': {'str': rel_str,
                                                'PID': rel_pid},
                                'object_true': {'str': obj_true_str,
                                                'QID': obj_true_qid},
                                'object_new': {'str': obj_edit_str,
                                                'QID': obj_edit_qid},
                                'sentence_template': sentence_template,
                                'paraphrase_prompts': paraphrase_prompts}
                new_triples.append(edit_triples)
            dataset[split][i]['triples'] = new_triples
    json.dump(dataset, open(args.dataset_file_path, 'w'), indent=4)

if __name__ == '__main__':
    args = parse_args()
    main(args)