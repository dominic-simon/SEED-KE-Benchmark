import random
import pywikibot
import mwparserfromhell

def get_obj(claim):
    if isinstance(claim.target, pywikibot._wbtypes.WbTime):
        obj = claim.target.year
    else:
        if isinstance(claim.target, type(None)):
            return None
        try:
            obj = claim.target.labels.get('en')
        except:
            return None
        if isinstance(obj, type(None)):
            obj = claim.target.labels.get('mul')
            if isinstance(obj, type(None)):
                return None
    return obj

def has_appropriate_dob_dod(data, claims, year=1725):
    if 'P569' in claims and 'P570' in claims:
        dob = data['claims']['P569'][0]
        dob = get_obj(dob)
        if isinstance(dob, type(None)):
            return False
        elif dob < year:
            return False
    else:
        return False
    return True

def has_long_enough_description(site, subj, data):
    wikipedia_page = pywikibot.Page(site, subj)
    try:
        text = wikipedia_page.text
    except:
        return None, None
    text = mwparserfromhell.parse(text)
    text = text.strip_code()
    wikipedia_description = text.split('\n')[0]
    wikidata_description = data['descriptions'].get('en')
    if isinstance(wikidata_description, type(None)) or len(wikipedia_description.split(' ')) < 5:
        return None, None
    return wikipedia_description, wikidata_description

def model_generation(model, tokenizer, prompt, max_new_tok=1000, temperature=1e-6):
    formatted_prompt = [{'role': 'system', 'content': 'Provide only the requested text.'},
                        {"role": "user", "content": prompt}]
    formatted_prompt = tokenizer.apply_chat_template(formatted_prompt,
                                                     tokenize=False,
                                                     add_generation_prompt=True,
                                                     enable_thinking=False)
    tok = tokenizer(formatted_prompt, return_tensors='pt').to(model.device)

    outputs = model.generate(tok.input_ids,
                             attention_mask=tok.attention_mask,
                             do_sample=True,
                             max_new_tokens=max_new_tok,
                             temperature=temperature)
    
    generated_text = tokenizer.decode(outputs[0][tok.input_ids.shape[1]:], skip_special_tokens=True)
    return generated_text