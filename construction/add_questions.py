import json
import random
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_file_path',
                        type=str,
                        default='../datasets/dataset.json')
    args = parser.parse_args()
    return args

def get_questions():
    question = {'P17': ['What country is SUBJ located in?',
                        'What is the country that SUBJ is located in?'],
                'P19': ['Where was SUBJ born?',
                        'What location was SUBJ born in?',
                        'Where is SUBJ originally from?',
                        'Where was SUBJ originally from?',
                        'Where was SUBJ birthed?',
                        'What is the birthplace of SUBJ?'],
                'P20': ['Where did SUBJ die?',
                        'Where did SUBJ pass away?',
                        'Where did SUBJ lose their life?',
                        'Where did SUBJ\'s life end?',
                        'Where is SUBJ\'s place of death?'],
                'P21': ['What is the sex of SUBJ?',
                        'What sex was SUBJ born as?'],
                'P22': ['Who is SUBJ\'s father?',
                        'Who was SUBJ fathered by?'],
                'P25': ['Who is SUBJ\'s mother?',
                        'Who was SUBJ mothered by?'],
                'P26': ['Who is SUBJ married to?',
                        'Who did SUBJ get married to?',
                        'Who is SUBJ\'s spouse?'],
                'P27': ['Where is SUBJ a citizen of?',
                        'Where does SUBJ hold a citizenship?',
                        'Where is SUBJ\'s citizenship?',
                        'What is the country of citizenship of SUBJ?'],
                'P39': ['What position does SUBJ hold?',
                        'What is the position of SUBJ?'],
                'P40': ['Who is SUBJ\'s child?',
                        'Who is the child of SUBJ?',
                        'Who is SUBJ the parent of?'],
                'P50': ['Who authored SUBJ?',
                        'Who was the author of SUBJ?',
                        'Who is SUBJ\'s author?',
                        'Who was SUBJ written by?',
                        'Who is the writer of SUBJ?',
                        'SUBJ was written by who?'],
                'P57': ['Who is the director of SUBJ?',
                        'The director of SUBJ is who?',
                        'From which director did SUBJ come from?'],
                'P58': ['Who was the screenwriter for SUBJ?',
                        'SUBJ\'s screenwriter was who?',
                        'The script for SUBJ was written by who?',
                        'Who wrote the script for SUBJ?'],
                'P69': ['Where was SUBJ educated at?',
                        'What school did SUBJ attend?'],
                'P86': ['Who composed the music in SUBJ?',
                        'Who was the composer for SUBJ?',
                        'The composer of SUBJ was who?',
                        'The music in SUBJ was composed by who?'],
                'P103': ['What is the native language of SUBJ?',
                        'What is the mother tongue of SUBJ?'],
                'P106': ['What does SUBJ work as?',
                        'What is SUBJ\'s occupation?',
                        'What is the occupation of SUBJ?',
                        'What is SUBJ\'s profession?',
                        'What is the profession of SUBJ?',
                        'What is SUBJ\'s job?'],
                'P108': ['Who does SUBJ work?',
                        'Who is SUBJ employed by?',
                        'Who is the employer of SUBJ?'],
                'P112': ['Who was SUBJ founded by?',
                        'Who is the founder of SUBJ?'],
                'P119': ['Where was SUBJ buried?',
                        'Where is the burial location of SUBJ?'],
                'P123': ['Who published SUBJ?',
                        'Who is the publisher of SUBJ?'],
                'P127': ['Who is SUBJ owned by?',
                        'Who is the owner of SUBJ?',
                        'Who is SUBJ\'s owner?'],
                'P136': ['What is SUBJ\'s genre?',
                        'What is the genre of SUBJ?',
                        'What genre does SUBJ belong to?'],
                'P140': ['What religion does SUBJ belong to?',
                        'What religion does SUBJ follow?',
                        'What religion is SUBJ a follower of?'],
                'P159': ['Where is the headquarters of SUBJ?',
                        'Where is SUBJ headquartered?',
                        'What is the headquarters location of SUBJ?',
                        'What location is SUBJ headquartered at?'],
                'P166': ['What award did SUBJ receive?',
                        'SUBJ is the recipient of what award?'],
                'P170': ['Who is the creator of SUBJ?',
                        'Who was SUBJ created by?',
                        'SUBJ\'s creator is who?'],
                'P178': ['Who is the developer of SUBJ?',
                        'Who was SUBJ developed by?',
                        'SUBJ\'s developer is who?',
                        'Who is SUBJ a product of?'],
                'P272': ['What is the film studio that made SUBJ?',
                        'What is the production company behind SUBJ?',
                        'What is the motion picture studio behind SUBJ?'],
                'P407': ['What was SUBJ written in?',
                        'What language was SUBJ written in?'],
                'P452': ['What industry does SUBJ participate in?'],
                'P463': ['What is SUBJ a member of?',
                        'What group or organization is SUBJ a member of?',
                        'What group or organization is SUBJ affiliated with?'],
                'P495': ['What is the country of origin of SUBJ?',
                        'What is SUBJ\'s country of origin?',
                        'Where did SUBJ originate from?'],
                'P509': ['What did SUBJ die from?',
                        'What was SUBJ killed by?',
                        'What was SUBJ\'s cause of death?'],
                'P560': ['Who is SUBJ related to?',
                        'To whom does SUBJ have a familial relation to?',
                        'Who is SUBJ part of the same family as?'],
                'P641': ['What sport did SUBJ play?',
                        'What sport does SUBJ play?'],
                'P740': ['Where was SUBJ founded?',
                        'Where was SUBJ formed?',
                        'Where was SUBJ created?'],
                'P749': ['What is the parent organization of SUBJ?',
                        'What is the parent organization of SUBJ called?',
                        'What is the name of the parent organization of SUBJ?'],
                'P800': ['What notable work did SUBJ create?',
                        'What is SUBJ famous for making?'],
                'P1344': ['What did SUBJ participant in?',
                        'What event was SUBJ a participant in?'],
                'P1412': ['What language does SUBJ communicate in?'],
                'P3373': ['Who are SUBJ\'s siblings?',
                        'Who is a sibling of SUBJ?',
                        'Who does SUBJ share the same parents as?']}
    return question

def add_questions(questions, dataset_file_path):
    with open(dataset_file_path, 'r') as f:
        ds = json.load(f)
    
    for split in ['clean', 'edit']:
        for case in ds[split]:
            for i in range(len(case['triples'])):
                qs = questions[case['triples'][i]['relation']['PID']]
                q = random.choice(qs)
                ds[split][case['case']]['triples'][i]['question'] = q
    
    json.dump(ds, open(dataset_file_path, 'w'), indent=4)


if __name__ == '__main__':
    random.seed(27)
    args = parse_args()
    q = get_questions()
    add_questions(q, args.dataset_file_path)