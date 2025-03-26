import json
import glob, os, re
from collections import defaultdict
from schema import SCHEMA
import argparse 

parser = argparse.ArgumentParser()

parser.add_argument('--pattern', type=str, choices=['cot', 'reflexion', 'autocrawler', 'autocrawler_extra'], help='Which type of crawler generation agent to use.')
parser.add_argument('--model', type=str, help='Backbone model')

args = parser.parse_args()
print(args)

PATTERN = args.pattern
model = args.model
# PATTERN = 'autocrawler'
# model = 'GPT4mini'

GROUND_TRUTH_HOME = 'data/ex_swde/sourceCode/groundtruth'
OUTPUT_HOME = f'dataset/ex_swde/{model}/{PATTERN}'

def load_file(filename, items):
    result_dict = {}
    with open(filename, 'r', encoding='utf8') as f:
        data = json.load(f)
        for field in items:
            field_dict = {}
            for key, value in data.items():
                field_id = key.replace('.htm', '')
                if field in value:
                    field_dict[field_id] = value[field]
                else:
                    field_dict[field_id] = []
            result_dict[field] = field_dict
    return result_dict


def normalize(text):
    #print(text_list)
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'").replace('&apos;', "'")
    text = text.replace('&#150;', '–')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&#160;', ' ')
    text = text.replace('&#039;', "'")
    text = text.replace('&#34;', '"')
    text = text.replace('&reg;', '®')
    text = text.replace('&rsquo;','’')
    text = text.replace('&#8226;','•')
    text = text.replace('&ndash;','–')
    text = text.replace('&#x27;', "'")
    text = text.replace('&#40;', '(')
    text = text.replace('&#41;', ')')
    text = text.replace('&#47;','/')
    text = text.replace('&#43;','+')
    text = text.replace('&#035;','#')
    text = text.replace('&#38;', '&')
    text = text.replace('&eacute;', 'é')
    text = text.replace('&frac12;', '½')
    text = re.sub(r"\s+", "", text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text.strip()

def normalize_list(text_list):
    return [normalize(text) for text in text_list if text and normalize(text)]

result_dict = {}
result_overall = {}
result_summary = {
    'Fully correct': 0,
    'Precision': 0,
    'Recall': 0,
    'Unexecute': 0,
    'Overestimate': 0,
    'Else': 0,
    'Total': 0,
    'Micro_p': 0.0,
    'Micro_r': 0.0,
    'Micro_f1': 0.0
}

for field in SCHEMA.keys():
    result_dict[field] = {}
    result_overall[field] = {}
    weblist = glob.glob(os.path.join(OUTPUT_HOME, field, '*'))
    weblist = [(os.path.normpath(web)).replace('\\', '/') for web in weblist]

    for website_path in weblist:
        if f'_{PATTERN}.json' in website_path:
            continue
        # if f'_rule' in website_path:
        #     continue
        print(website_path)
        website_name = website_path.split('/')[-1].replace('.json', '')
        result_dict[field][website_name] = {}
        
        filename = os.path.join(GROUND_TRUTH_HOME, f'{field}.json')
        ground_truth = load_file(filename, SCHEMA[field])
        
        with open(website_path, 'r', encoding='utf8') as f:
            predict_result = json.load(f)
        #print(predict_result)
        tp = defaultdict(int)
        tn = defaultdict(int)
        fp = defaultdict(int)

        for result in predict_result:
            # page_index = result['page'].split('/')[-1].replace('.htm', '')
            page_index = result['page'].split('\\')[-1].replace('.htm', '')
            result_dict[field][website_name][page_index] = {}
            for item in SCHEMA[field]:
                #print(result)
                result_dict[field][website_name][page_index][item] = {}
                pred = set(normalize_list(result[item]))
                gt = set(normalize_list(ground_truth[item][page_index]))
                result_dict[field][website_name][page_index][item]['pred'] = list(pred)
                result_dict[field][website_name][page_index][item]['ground_truth'] = list(gt)

                tp[item] += len(pred & gt)
                fp[item] += len(pred - gt)
                tn[item] += len(gt - pred)

        result_overall[field][website_name] = {}
        for item in SCHEMA[field]:
            p = (tp[item] + 1e-12) / (fp[item] + tp[item] + 1e-12)
            r = (tp[item] + 1e-12) / (tp[item] + tn[item] + 1e-12)
            f1 = (2 * p * r) / (p + r + 1e-12)
            result_overall[field][website_name][item] = {
                'Precision': round(p, 4),
                'Recall': round(r, 4),
                'F1': round(f1, 4),
                'TP': tp[item],
                'FP': fp[item],
                'TN': tn[item]
            }
            #print(p)
            if round(f1, 4) == 1.00:
                result_summary['Fully correct'] += 1
            elif (round(p, 4) == 1.00) and (round(r, 4) != 0.00):
                result_summary['Precision'] += 1
            elif (round(r, 4) == 1.00) and (round(p, 4) != 0.00):
                result_summary['Recall'] += 1
            elif (round(r, 4) == 0.00):
                result_summary['Unexecute'] += 1
            elif (round(p, 4) == 0.00):
                result_summary['Overestimate'] += 1
            else:
                result_summary['Else'] += 1
            result_summary['Total'] += 1
            result_summary['Micro_p'] += p
            result_summary['Micro_r'] += r
            result_summary['Micro_f1'] += f1

for key in result_summary.keys():
    if key != 'Total':
        result_summary[key] = round(result_summary[key] / result_summary['Total'], 4)

print(json.dumps(result_summary, indent=4))
with open(os.path.join(OUTPUT_HOME, 'result.json'), 'w', encoding='utf8') as f:
    json.dump(result_dict, f, ensure_ascii=False, indent=4)

with open(os.path.join(OUTPUT_HOME, 'result_overall.json'), 'w', encoding='utf8') as f:
    json.dump(result_overall, f, ensure_ascii=False, indent=4)

with open(os.path.join(OUTPUT_HOME, 'result_summary.json'), 'w', encoding='utf8') as f:
    json.dump(result_summary, f, ensure_ascii=False, indent=4)