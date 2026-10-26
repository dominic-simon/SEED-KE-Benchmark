import torch

import numpy as np
from scipy.stats.mstats import gmean

from bert_score import BERTScorer
from sacrebleu.metrics import BLEU, CHRF, TER

import nltk
import string
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

if False:
    nltk.download('punkt', download_dir='./nltk_data/')
    nltk.download('punkt_tab', download_dir='./nltk_data/')
    nltk.download('stopwords', download_dir='./nltk_data/')
nltk.data.path.append('/<YOUR_PATH_TO_NLTK_DATA>/nltk_data/')

scorer = BERTScorer(model_type='microsoft/deberta-xlarge-mnli', device='cuda:0' if torch.cuda.is_available() else 'cpu')

def string_matching(clean_text, edit_text, object_new_list, object_true_list):
    print(object_true_list)
    print(object_new_list)
    if len(object_true_list) != len(object_new_list):
        print(f'In string matching, the two lists are different lengths.\n{object_true_list}\n{object_new_list}')
        return 0, 0, 0, 0, 0, 0
    if len(object_true_list) == 0 or len(object_new_list) == 0:
        print(f'In string matching, one of the two lists has a length of 0.\n{object_true_list}\n{object_new_list}')
        return 0, 0, 0, 0, 0, 0

    true_true_incl = 0
    true_alias_incl = 0
    new_incl_clean = []
    for obj in object_true_list:
        if obj['orig'] in clean_text:
            true_true_incl += 1
            new_incl_clean.append((obj['orig'], 'obj'))
        else:
            miss = True
            for alias in obj['alias']:
                if alias in clean_text:
                    true_alias_incl += 1
                    new_incl_clean.append((alias, 'alias'))
                    miss = False
                    break
            if miss:
                new_incl_clean.append((None, 'miss'))
    before_hits_alias = 0
    new_hits_alias = 0
    before_hits_true = 0
    new_hits_true = 0
    for i, obj in enumerate(object_new_list):
        if obj['orig'] in edit_text:
            if new_incl_clean[i][1] in ['obj', 'alias']:
                before_hits_true += 1
            else:
                new_hits_true += 1
        else:
            for alias in obj['alias']:
                if alias in edit_text:
                    if new_incl_clean[i][1] in ['obj', 'alias']:
                        before_hits_alias += 1
                    else:
                        new_hits_alias += 1
    return before_hits_alias, new_hits_alias, before_hits_true, new_hits_true, true_true_incl, true_alias_incl

def bert_score(ref_text, gen_text):
    global scorer
    _, _, f1 = scorer.score([gen_text], [ref_text])
    return f1

def compute_bleu(ref_text, gen_text, max_ngram=4):
    scorer = BLEU(lowercase=False, max_ngram_order=max_ngram)
    return scorer.corpus_score(hypotheses=[gen_text], references=[[ref_text]]).score

def compute_chrf(ref_text, gen_text):
        scorer = CHRF()
        return scorer.corpus_score(hypotheses=[gen_text], references=[[ref_text]]).score

def compute_ter(ref_text, gen_text):
        scorer = TER(normalized=False, no_punct=False, case_sensitive=False)
        return scorer.corpus_score(hypotheses=[gen_text], references=[[ref_text]]).score

def compute_ngram_entropy(text, ngram_val=[2, 3]):
    '''
    from ROME
    '''
    weights = [2 / 3, 4 / 3]

    entropy_list = []
    for n in ngram_val:
        tokens = nltk.word_tokenize(text)
        ngrams = nltk.ngrams(tokens, n)
        fdist = nltk.FreqDist(ngrams)
        freqs = np.array([freq for _, freq in fdist.items()])
        freqs = freqs / freqs.sum()

        entropy_list.append(np.sum(-freqs * np.log(freqs) / np.log(2)))

    entropy_list = np.array(entropy_list) * np.array(weights)

    return gmean(entropy_list)

def compute_rouge_n(ref_text, gen_text, ngram_val=[2, 3, 4]):
    ref_ngrams = get_ngrams(ref_text, ngram_val=ngram_val)
    gen_ngrams = get_ngrams(gen_text, ngram_val=ngram_val)
    
    rouge_scores = {}
    for n in ngram_val:
        overlap_sum = get_ngram_overlap(ref_ngrams[n], gen_ngrams[n])

        if len(ref_ngrams[n]) == 0:
            rouge_scores[n] = 0.0
        else:
            rouge_scores[n] = overlap_sum / len(ref_ngrams[n])

    return rouge_scores

def get_ngrams(text, ngram_val=[2, 3, 4]):
    stop_words = set(stopwords.words('english'))
    stop_words.update(set(string.punctuation))
    text = [word.lower() for word in word_tokenize(text) if word.lower() not in stop_words]
    all_ngrams = {}
    for n in ngram_val:
        all_ngrams[n] = [' '.join(text[i:i+n]) for i in range(len(text)) if len(text[i:i+n]) == n]
    return all_ngrams

def get_ngram_overlap(ref, candidate):
        overlap_sum = 0
        overlapping_ngrams = set(ref) & set(candidate)
        for ngram in overlapping_ngrams:
            overlap_sum += min(ref.count(ngram), candidate.count(ngram))
        return overlap_sum

def perplexity(model, tokenizer, text, device='cuda:0'):
    '''
    from ROME
    '''
    inputs = tokenizer([text], return_tensors='pt', add_special_tokens=False).to(device)

    logits = torch.nn.functional.log_softmax(model(**inputs).logits, dim=-1)
    log_probs = torch.gather(logits[:, :-1, :], -1, inputs['input_ids'][:, 1:, None])[0]

    # Perplexity = exp(-1/N * log P(x_1, ..., x_n))
    return torch.exp(-1 / inputs['input_ids'].size(1) * log_probs.sum()).item()

def edit_recall_score(model, tokenizer, edit_sentences, object_true, object_new, device='cuda:0'):
    binary_acc, magnitude_diff = 0, 0

    for i in range(len(edit_sentences)):
        sentence_tok_len = tokenizer(edit_sentences[i], return_tensors='pt', add_special_tokens=False).input_ids.shape[1]
        sentences = [f'{edit_sentences[i]} {obj}' for obj in [object_true[i], object_new[i]]]
        sentences_tok = tokenizer(sentences, padding=True, return_tensors='pt', add_special_tokens=False).to(device)
        
        true_tok, new_tok = (tokenizer(f' {obj}', return_tensors='pt', add_special_tokens=False).input_ids[0] for obj in [object_true[i], object_new[i]])
        true_tok_len, new_tok_len = (len(tok) for tok in [true_tok, new_tok])
        
        with torch.no_grad():
            logits = model(**sentences_tok).logits

        results = torch.zeros(logits.shape[0])
        for j in range(logits.shape[0]):
            current_len = true_tok_len if j % 2 == 0 else new_tok_len
            current_obj = true_tok if j % 2 == 0 else new_tok
            for k in range(current_len):
                current_tok = current_obj[k]
                results[j] += -torch.nn.functional.log_softmax(logits[j, (sentence_tok_len-1)+k, :], dim=0)[current_tok].item()
            results[j] /= current_len

        magnitude_diff += (torch.exp(-results[1]) - torch.exp(-results[0]))
        if results[0] > results[1]:
            binary_acc += 1
    
    return binary_acc, magnitude_diff

def edit_generality_score(model, tokenizer, paraphrase_prompts, object_true, object_new, device='cuda:0'):
    binary_acc, magnitude_diff = 0, 0

    for i in range(len(paraphrase_prompts)):
        for prompt in paraphrase_prompts[i]:
            new_acc, new_diff = edit_recall_score(model, tokenizer, [prompt], [object_true[i]], [object_new[i]], device=device)
            binary_acc += new_acc
            magnitude_diff += new_diff
    
    return binary_acc, magnitude_diff

def multi_edit_eval(model, tokenizer, paragraph, object_true, object_new, device):
    acc_single, acc_global, mag_diff, total = 0, 0, 0, 0
    for i in range(len(object_true)):
        if object_true[i] in paragraph:
            splits = paragraph.split(f' {object_true[i]}')

            if len(splits) > 1:
                prefix, suffix = splits[0], splits[1]
                total += 1
        
                binary_acc, mag = edit_recall_score(model, tokenizer, [prefix], [object_true[i]], [object_new[i]], device)
                acc_single += binary_acc
                mag_diff += mag

                paragraph = f'{prefix} {object_new[i]}{suffix}'

    if acc_single == total and total > 0:
        acc_global += 1
            
    return acc_global, acc_single, mag_diff, total

def edit_nbh_score(model, tokenizer, nbh_prompts, nbh_true, object_new, device='cuda:0'):
    binary_acc, magnitude_diff = 0, 0

    for i in range(len(nbh_prompts)):
        sentence_tok_len = tokenizer(nbh_prompts[i], return_tensors='pt', add_special_tokens=False).input_ids.shape[1]

        edit_obj_results = torch.zeros(1+len(object_new))

        for j in range(len(object_new)):
            nbh_sentence = f'{nbh_prompts[i]} {object_new[j]}'
            nbh_sentence_tok = tokenizer(nbh_sentence, return_tensors='pt', add_special_tokens=False).to(device)
            new_tok = tokenizer(f' {object_new[j]}', return_tensors='pt', add_special_tokens=False).input_ids[0]
            new_tok_len = len(new_tok)

            with torch.no_grad():
                logits = model(**nbh_sentence_tok).logits

            for k in range(new_tok_len):
                current_tok = new_tok[k]
                edit_obj_results[j+1] += -torch.nn.functional.log_softmax(logits[0, (sentence_tok_len-1)+k, :], dim=0)[current_tok].item()
            edit_obj_results[j+1] /= new_tok_len
        
        nbh_sentence = f'{nbh_prompts[i]} {nbh_true[i]}'
        nbh_sentence_tok = tokenizer(nbh_sentence, return_tensors='pt', add_special_tokens=False).to(device)
        true_tok = tokenizer(f' {nbh_true[i]}', return_tensors='pt', add_special_tokens=False).input_ids[0]
        true_tok_len = len(true_tok)

        with torch.no_grad():
            logits = model(**nbh_sentence_tok).logits

        for j in range(true_tok_len):
            current_tok = true_tok[j]
            edit_obj_results[0] += -torch.nn.functional.log_softmax(logits[0, (sentence_tok_len-1)+j, :], dim=0)[current_tok].item()
        edit_obj_results[0] /= true_tok_len

        magnitude_diff += (torch.exp(-edit_obj_results[0]) - torch.exp(-torch.min(edit_obj_results[1:])))

        min_idx = torch.argmin(edit_obj_results).item()
        if min_idx == 0:
            binary_acc += 1
        elif torch.isclose(edit_obj_results[min_idx], edit_obj_results[0], rtol=0.0, atol=1e-4):
            binary_acc += 1
    
    return binary_acc, magnitude_diff  