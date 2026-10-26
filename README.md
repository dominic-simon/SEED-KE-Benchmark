# Beyond Single Edits: Rethinking Knowledge Editing Evaluation with Multi-Edit Entities and Undirected Probing

This is the repository for [Beyond Single Edits: Rethinking Knowledge Editing Evaluation with Multi-Edit Entities and Undirected Probing](https://openreview.net/forum?id=H8QZxXdf1O), which is published at the 2026 Findings of the Empirical Methods for Natural Language Processing (EMNLP Findings 2026). 

## Dataset and Dataset Construction

The `/datasets/` folder contains the three SEED subsets. They are zipped together as `/datasets/datasets.zip` and should be unzipped for use. The files are formatted using the `.json` file format.

The `/construction/` folder contains all of the scripts and information used to generate the dataset. The `/construction/construct_art.sh`, `/construction/construct_business.sh`, and `/construction/construct_person.sh` files can be used to generate unique datasets following the same process described in the manuscript. However, the Wikidata access rates have been significantly reduced since the creation of this dataset, so the time required to generate a dataset using these exact files has likely increased dramatically.

## Metrics

The `metrics.py` file contains all metrics used in the evaluations. They are labeled with comments in the python file.

# UNDER CONSTRUCTION

I apologize for this repository not being ready. I will be cleaning and adding more files in the coming weeks. 
