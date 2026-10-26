#!/bin/bash

NUM_ENTITIES=1200
FINAL_DS_SIZE=1000
SLICE_SIZE=2
ENTITY_TYPES="place"
ENTITY_STR="business public_company fast_food_restaurant_chain enterprise retail_chain technology_company restaurant_chain video_game_developer video_game_publisher publishing_company book_publisher"
ENTITY_QID="Q4830453 Q891723 Q18509232 Q6881511 Q507619 Q18388277 Q18534542 Q210167 Q1137109 Q2085381 Q1320047"
HF_LOGIN_TOKEN="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"
HF_MODEL_PATH="meta-llama/Llama-3.1-8B-Instruct"
RELATION_FILE_PATH="./relations.json"
EXCLUSION_FILE_PATH="./exclusion_properties.json"
SENTENCE_TEMPLATE_PATH="./sentence_templates.json"
DATASET_FILE_PATH="../datasets/business.json"

echo "Removing previous version of the dataset.."
rm "$DATASET_FILE_PATH"

echo "Creating Edits..."
python3 generate_triples.py --split edit --num_entities "$NUM_ENTITIES" --entity_types "$ENTITY_TYPES" --entity_str "$ENTITY_STR" --QID "$ENTITY_QID" --relation_file_path "$RELATION_FILE_PATH" --dataset_file_path "$DATASET_FILE_PATH"
python3 insert_edits.py --entity_str "$ENTITY_STR" --QID "$ENTITY_QID" --exclusion_file_path "$EXCLUSION_FILE_PATH" --dataset_file_path "$DATASET_FILE_PATH"
python3 make_paragraph.py --split edit --slice_size "$SLICE_SIZE" --hf_model_path "$HF_MODEL_PATH" --dataset_file_path "$DATASET_FILE_PATH" --hf_login_token "$HF_LOGIN_TOKEN"
python3 make_sentences_from_triples.py --split edit --triple_type edit_triples --sentence_template_path "$SENTENCE_TEMPLATE_PATH" --dataset_path "$DATASET_FILE_PATH"
python3 make_sentences_from_triples.py --split edit --triple_type triples --sentence_template_path "$SENTENCE_TEMPLATE_PATH" --dataset_path "$DATASET_FILE_PATH"
python3 make_paraphrases.py --num_paraphrases 3 --hf_model_path "$HF_MODEL_PATH" --dataset_file_path "$DATASET_FILE_PATH" --hf_login_token "$HF_LOGIN_TOKEN"

echo "Getting Clean Samples..."
python3 generate_triples.py --split clean --num_entities "$NUM_ENTITIES" --entity_types "$ENTITY_TYPES" --entity_str "$ENTITY_STR" --QID "$ENTITY_QID" --exclusion_file_path "$EXCLUSION_FILE_PATH" --relation_file_path "$RELATION_FILE_PATH" --dataset_file_path "$DATASET_FILE_PATH"
python3 make_paragraph.py --split clean --slice_size "$SLICE_SIZE" --hf_model_path "$HF_MODEL_PATH" --dataset_file_path "$DATASET_FILE_PATH" --hf_login_token "$HF_LOGIN_TOKEN"
python3 make_sentences_from_triples.py --split clean --triple_type triples --sentence_template_path "$SENTENCE_TEMPLATE_PATH" --dataset_path "$DATASET_FILE_PATH"

echo "Cleaning up the dataset file..."
python3 cleaning.py --dataset_file_path "$DATASET_FILE_PATH"
python3 further_cleaning.py --dataset_file_path "$DATASET_FILE_PATH"
python3 add_questions.py --dataset_file_path "$DATASET_FILE_PATH"
python3 add_object_aliases.py --dataset_file_path "$DATASET_FILE_PATH"
python3 set_to_n_cases.py --dataset_path "$DATASET_FILE_PATH" --ds_size "$FINAL_DS_SIZE"