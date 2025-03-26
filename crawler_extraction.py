import glob
import json, os, sys
from tqdm import tqdm
from utils.html_utils import *
from module.stepback_crawler import StepbackCrawler
from module.reflexion_crawler import AutoCrawler
from module.stepback_extra_crawler import StepbackExtraCrawler
from module.prompt import *

import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--pattern', type=str, choices=['cot', 'reflexion', 'autocrawler', 'autocrawler_extra'], help='Which type of crawler generation agent to use.')
parser.add_argument('--model', type=str, help='Backbone model')
parser.add_argument('--dataset', type=str, choices=['swde','ds1','ex_swde','klarna', 'weir'], help='Which dataset to test.')
parser.add_argument('--save_name', type=str)
parser.add_argument('--overwrite', type=str, help='Whether overwrite the generated crawler.')

args = parser.parse_args()
print(args)

PATTERN = args.pattern
model = args.model
dataset = args.dataset
overwrite = eval(args.overwrite)
if args.save_name:
    OUTPUT_HOME = f'dataset/{dataset}/{args.save_name}/{PATTERN}'
else:
    OUTPUT_HOME = f'dataset/{dataset}/{model}/{PATTERN}'

# PATTERN = 'autocrawler_extra'
# model = 'GPT4mini'
# dataset = 'weir'
# overwrite = False
# OUTPUT_HOME = f'dataset/{dataset}/{model}/{PATTERN}'

if PATTERN == 'autocrawler':
    xe = StepbackCrawler(api='None')
    extract = xe.extract_with_sequence
elif PATTERN == 'autocrawler_extra':
    xe = StepbackExtraCrawler(api='None')
    extract = xe.extract_with_sequence
else:
    xe = AutoCrawler(PATTERN, api='None')
    extract = xe.extract_with_xpath

if dataset == 'swde':
    from run_swde.task_prompt import swde_prompt as prompt
    SCHEMA = {
        'auto': ['model', 'price', 'engine', 'fuel_economy'],
        'book': ['title', 'author', 'isbn_13', 'publisher', 'publication_date'],
        'camera': ['model', 'price', 'manufacturer'],
        'job': ['title', 'company', 'location', 'date_posted'],
        'movie': ['title', 'director', 'genre', 'mpaa_rating'],
        'nbaplayer': ['name', 'team', 'height', 'weight'],
        'restaurant': ['name', 'address', 'phone', 'cuisine'],
        'university': ['name', 'phone', 'website', 'type']
    }
    DATA_HOME = 'data/swde/sourceCode'
    filter_website = []
elif dataset == 'ds1':
    from run_ds1.task_prompt import ds1_prompt as prompt
    SCHEMA = {
        'book': ['title', 'author', 'price'],
        'e-commerce': ['title', 'price'],
        'hotel': ['title', 'price', 'address'],
        'movie': ['title', 'genre', 'actor']
    }
    DATA_HOME = 'data/ds1/Web/FX-dataset/trainingset'
    if model == 'ChatGPT':
        filter_website = ['shoppings_bestbuy', 'shoppings_pcworld', 'shoppings_uttings', 'shoppings_amazoncouk', 'shoppings_tesco', 'kayak', 'ratestogo', 'expedia', 'hotels', 'venere', 'rottentomatoes', 'metacritic', 'imdb']
    else:
        filter_website = []
elif dataset == 'ex_swde':
    from run_swde_et.schema import SCHEMA
    DATA_HOME = 'data/ex_swde/sourceCode'
    filter_website = []
elif dataset == 'klarna':
    from run_klarna.task_prompt import klarna_prompt as prompt
    SCHEMA = {
        'product': ['name', 'price'],
    }
    filter_website = []
    DATA_HOME = 'data/klarna_product_page_dataset_WTL_50k/train/US'
elif dataset == 'weir':
    from run_weir.task_prompt import weir_prompt as prompt
    from run_weir.schema import SCHEMA
    DATA_HOME = 'data/weir/sourceCode'
    filter_website = []

for field in SCHEMA.keys():
    if not os.path.exists(os.path.join(OUTPUT_HOME, field)):
        os.makedirs(os.path.join(OUTPUT_HOME, field))

    if dataset == 'swde':
        weblist = glob.glob(os.path.join(DATA_HOME, field, '*'))
    elif dataset == 'ds1':
        fake_item = SCHEMA[field][0]
        weblist = glob.glob(os.path.join(DATA_HOME, field, fake_item, '*'))
    elif dataset == 'ex_swde':
        field0, field1 = field.split('-')
        print(os.path.join(DATA_HOME, field))
        if os.path.exists(os.path.join(DATA_HOME, field)):
            weblist = [os.path.join(DATA_HOME, field)]
        else:
            weblist = []
    elif dataset == 'klarna':
        weblist = glob.glob(os.path.join(DATA_HOME, '*'))
    elif dataset == 'weir':
        weblist = glob.glob(os.path.join(DATA_HOME, field, '*'))

    weblist = [(os.path.normpath(web)).replace('\\', '/') for web in weblist]

    for website_path in weblist:
        if dataset in ['ex_swde', 'swde']:
            website_name = website_path.split('/')[-1].split('(')[0]
        elif dataset == 'ds1':
            website_name = website_path.split('/')[-1].replace(f'{field}_','').replace(f'_{fake_item}.html','')
        elif dataset == 'klarna':
            website_name = website_path.split('/')[-1]
        elif dataset == 'weir':
            website_name = field + '-' + website_path.split('/')[-1]
        
        if os.path.exists(os.path.join(OUTPUT_HOME, field, website_name) + '.json') and (not overwrite):
            continue
        
        xpath_rule = {}
        # sorted(webpage_list)
        if not os.path.exists(os.path.join(OUTPUT_HOME, field, website_name) + f'_{PATTERN}.json'):
            continue
        with open(os.path.join(OUTPUT_HOME, field, website_name) + f'_{PATTERN}.json', mode='r', errors='ignore') as f:
            xpath_rule = json.load(f)

        # Rule execution
        result_list = []
        
        print(website_name)
        # web_index = webpage.split('/')[-1].replace('.htm','')
        if dataset in ['swde', 'ex_swde']:
            webpage_list = glob.glob(os.path.join(website_path, '*'))
            sorted(webpage_list)
            for webpage in tqdm(webpage_list[:100]):
                web_index = webpage.split('/')[-1].replace('.htm','')

                with open(webpage, 'r', errors='ignore', encoding="utf8") as f:
                    html = f.read()
                
                new_res = {'page': web_index}
                for item in SCHEMA[field]:
                    item_value = extract(html, xpath_rule.get(item, []))
                    new_res[item] = item_value

                result_list.append(new_res)
        elif dataset == 'ds1':
            with open(website_path, 'r', errors='ignore') as f:
                html = f.read()
            
            new_res = {'page': 0}
            for item in SCHEMA[field]:
                item_value = extract(html, xpath_rule[item])
                new_res[item] = item_value

            result_list.append(new_res)
        elif dataset == 'klarna':
            webpage_list = glob.glob(os.path.join(website_path, '*', 'source.html'))
            for webpage in webpage_list:
                web_index = webpage.split('/')[-2]
                with open(webpage, 'r', errors='ignore') as f:
                    html = f.read()
                
                new_res = {'page': web_index}
                for item in SCHEMA[field]:
                    item_value = extract(html, xpath_rule[item])
                    new_res[item] = item_value

                    #print(item, item_value)
                result_list.append(new_res)
        elif dataset == 'weir':
            webpage_list = glob.glob(os.path.join(website_path, '*'))
            sorted(webpage_list)
            for webpage in tqdm(webpage_list[:100]):
                web_index = webpage.split('/')[-1].replace('.html','')

                with open(webpage, 'r', errors='ignore', encoding="utf8") as f:
                    html = f.read()
                
                new_res = {'page': web_index}
                for item in SCHEMA[field]:
                    item_value = extract(html, xpath_rule[item])
                    new_res[item] = item_value

                result_list.append(new_res)

        # with open(os.path.join(tmp_out, field, website_name) + '.json', 'w', encoding="utf8") as f:
        with open(os.path.join(OUTPUT_HOME, field, website_name) + '.json', 'w', encoding='utf8', errors='ignore') as f:
            json.dump(result_list, f, indent=4)