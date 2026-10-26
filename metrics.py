import torch

import numpy as np
from scipy.stats.mstats import gmean

from bert_score import BERTScorer
from sacrebleu.metrics import BLEU, CHRF

import nltk
import string
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Set to True if these nltk packages have not been downloaded before. 
# Otherwise, set to False to avoid output clutter.
if False:
    nltk.download('punkt', download_dir='./nltk_data/')
    nltk.download('punkt_tab', download_dir='./nltk_data/')
    nltk.download('stopwords', download_dir='./nltk_data/')
nltk.data.path.append('/<YOUR_PATH_TO_NLTK_DATA>/nltk_data/')

# Used for semantic similarity.
# It is faster to globally load it than to re-load it on every metric call.
scorer = BERTScorer(model_type='microsoft/deberta-xlarge-mnli', device='cuda:0' if torch.cuda.is_available() else 'cpu')

# String Matching metric
def string_matching(pre_edit_outputs, f_post, object_new_list, object_true_list):
    if not (len(pre_edit_outputs) == len(object_new_list)== len(object_true_list)):
        raise ValueError("The pre-edit outputs and object lists must have equal lengths.")

    def get_candidates(obj):
        return [value for value in [obj["orig"], *obj.get("alias", [])] if value]

    def contains_any(text, candidates):
        return any(candidate in text for candidate in candidates)
        
    H = []

    for i, h in enumerate(pre_edit_outputs):
        true_candidates = get_candidates(object_true_list[i])

        if contains_any(h, true_candidates):
            H.append((i, h))
            
    if not H:
        return 0.0
        
    hits = 0

    for i, h in H:
        post_text = f_post(h)
        new_candidates = get_candidates(object_new_list[i])

        if contains_any(post_text, new_candidates):
            hits += 1

    return hits / len(H)

# BERT Score (Semantic Similarity)
def bert_score(ref_text, gen_text):
    global scorer
    _, _, f1 = scorer.score([gen_text], [ref_text])
    return f1

# BLEU Score (Lexical Similarity)
def compute_bleu(ref_text, gen_text, max_ngram=4):
    scorer = BLEU(lowercase=False, max_ngram_order=max_ngram)
    return scorer.corpus_score(hypotheses=[gen_text], references=[[ref_text]]).score

# chrF (Lexical Similarity)
def compute_chrf(ref_text, gen_text):
        scorer = CHRF()
        return scorer.corpus_score(hypotheses=[gen_text], references=[[ref_text]]).score

# Edit Score (ES)
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

# Generality Score (GS)
def edit_generality_score(model, tokenizer, paraphrase_prompts, object_true, object_new, device='cuda:0'):
    binary_acc, magnitude_diff = 0, 0

    for i in range(len(paraphrase_prompts)):
        for prompt in paraphrase_prompts[i]:
            new_acc, new_diff = edit_recall_score(model, tokenizer, [prompt], [object_true[i]], [object_new[i]], device=device)
            binary_acc += new_acc
            magnitude_diff += new_diff
    
    return binary_acc, magnitude_diff

# Compound Probing Score & Compound Probing Perfect Score (CPS & CPPS)
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

# Neighborhood Score (NS)
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
