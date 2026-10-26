import json
import random
import argparse
from tqdm import tqdm

def parse_args():
      parser = argparse.ArgumentParser()
      parser.add_argument('--dataset_path',
                           type=str,
                           default='../datasets/dataset.json')
      parser.add_argument('--ds_size',
                           type=int,
                           default=100)
      args = parser.parse_args()
      return args

def main(ds_file_path, n=1000):
        with open(ds_file_path, 'r') as file:
              dataset = json.load(file)
        
        new_ds = {}
        for split in dataset.keys():
                counter = 0
                new_ds[split] = []
                for case in dataset[split]:
                        if counter > n-1:
                                break
                    
                        edit_counter = 0
                        for trips in case['triples']:
                                if not isinstance(trips['object_new']['str'], type(None)):
                                        edit_counter += 1
                        if edit_counter > 1 or split == 'clean':
                                new_ds[split].append(case)
                                counter += 1
        
        json.dump(new_ds, open(f'{ds_file_path[:-5]}_final.json', 'w'), indent=4)

if __name__ == '__main__':
      random.seed(82)

      args = parse_args()
      main(args.dataset_path, args.ds_size)