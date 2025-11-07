import glob
import json, os
import random
import logging
import traceback
from utils.html_utils import *
from module.stepback_crawler import StepbackCrawler
from module.reflexion_crawler import AutoCrawler
from module.stepback_extra_crawler import StepbackExtraCrawler
import argparse


def logging_setup():
    logger = logging.getLogger('crawler')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s\n%(message)s',
        datefmt='%m-%d %H:%M:%S'
        )

    file_handler = logging.FileHandler('crawler.log', encoding='utf-8', mode='w')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger
logger = logging_setup()

# parser = argparse.ArgumentParser()
# parser.add_argument('--pattern', type=str, choices=['cot', 'reflexion', 'autocrawler', 'autocrawler_extra'], help='Which type of crawler generation agent to use.')
# parser.add_argument('--model', type=str, help='Backbone model')
# parser.add_argument('--dataset', type=str, choices=['swde','ds1','ex_swde', 'klarna', 'weir'], help='Which dataset to test.')
# parser.add_argument('--seed_website', type=int)
# parser.add_argument('--save_name', type=str)
# parser.add_argument('--overwrite', type=str, help='Whether overwrite the generated crawler.')
# parser.add_argument('--max_token', type=int)
# args = parser.parse_args()
# logger.info(args)

# PATTERN = args.pattern
# model = args.model
# dataset = args.dataset
# num_seed_website = args.seed_website
# overwrite = eval(args.overwrite)
# if args.max_token:
#     max_token = args.max_token
# else:
#     max_token = 8000

# os detect

PATTERN = 'autocrawler_extra'
model = 'GPT4mini'
dataset = 'news'
num_seed_website = 3
overwrite = False
max_token = 50000
OUTPUT_HOME = f'dataset/{dataset}/{model}'
# OUTPUT_HOME = f'dataset/{dataset}/{save_name}'

# if os.name == 'nt':
#     if args.save_name:
#         OUTPUT_HOME = f'dataset/{dataset}/{args.save_name}'
#     else:
#         OUTPUT_HOME = f'dataset/{dataset}/{model}'
# else:
#     # linux
#     if args.save_name:
#         OUTPUT_HOME = f'/root/autodl-fs/dataset/{dataset}/{args.save_name}'
#     else:
#         OUTPUT_HOME = f'/root/autodl-fs/dataset/{dataset}/{model}'


logger.info(f'max_token: {max_token}')

if model == 'GPT4mini':
    from utils.ms_api_copy import ms_gtp4_mini as llmapi
elif model == 'Claude3Haiku':
    from utils.claude3_api import claude3_haiku as llmapi
elif model == 'deepseek':
    from utils.custom_api import deepseek_33b_api as llmapi
elif model == 'phi':
    from utils.custom_api import phi3_api as llmapi
elif model == 'mixtral':
    from utils.custom_api import mixtral_87_api as llmapi
elif model == 'llama3':
    from utils.api import llama3 as llmapi

if PATTERN == 'autocrawler':
    xe = StepbackCrawler(api=llmapi)
elif PATTERN == 'autocrawler_extra':
    xe = StepbackExtraCrawler(api=llmapi)
else:
    xe = AutoCrawler(PATTERN, api=llmapi)

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
    filter_website = ['book-amazon']

elif dataset == 'ds1':
    from run_ds1.task_prompt import ds1_prompt as prompt
    SCHEMA = {
        'book': ['title', 'author', 'price'],
        'e-commerce': ['title', 'price'],
        'hotel': ['title', 'price', 'address'],
        'movie': ['title', 'genre', 'actor']
    }
    DATA_HOME = 'data/ds1/Web/FX-dataset/trainingset'
    if num_seed_website > 1:
        logger.info('DS1 only have one seed websites in dataset.')
        num_seed_website = 1
    if model == 'ChatGPT':
        filter_website = ['shoppings_bestbuy', 'shoppings_pcworld', 'shoppings_uttings', 'shoppings_amazoncouk', 'shoppings_tesco', 'kayak', 'ratestogo', 'expedia', 'hotels', 'venere', 'rottentomatoes', 'metacritic', 'imdb']
    else:
        filter_website = []
elif dataset == 'ex_swde':
    from run_swde_et.schema import SCHEMA
    from run_swde_et.task_prompt import ex_swde_prompt as prompt
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
    from run_weir.schema import SCHEMA
    from run_weir.task_prompt import weir_prompt as prompt
    
    DATA_HOME = 'data/weir/sourceCode'
    filter_website = []
elif dataset == 'news':
    from run_news.task_prompt import news_prompt as prompt
    DATA_HOME = 'data/news/sourceCode'
    SCHEMA = {
        'news': ['content']
    }
    filter_website = []

def load_file(filename):
    result_dict = {}
    with open(filename, 'r', encoding="utf8", errors='ignore') as f:
        for index, line in enumerate(f.readlines()):
            if index <= 1: 
                continue
            item_list = line.strip().split('\t')
            #logger.info(item_list)
            result_dict[item_list[0]] = item_list[2 : 2+int(item_list[1])]
    return result_dict

for field in SCHEMA.keys():
    if not os.path.exists(os.path.join(OUTPUT_HOME, PATTERN, field)):
        os.makedirs(os.path.join(OUTPUT_HOME, PATTERN, field))

    if dataset == 'swde':
        weblist = glob.glob(os.path.join(DATA_HOME, field, '*'))
    elif dataset == 'ds1':
        fake_item = SCHEMA[field][0]
        weblist = glob.glob(os.path.join(DATA_HOME, field, fake_item, '*'))
    elif dataset == 'ex_swde':
        field0, field1 = field.split('-')
        if os.path.exists(os.path.join(DATA_HOME, field)):
            weblist = [os.path.join(DATA_HOME, field)]
        else:
            weblist = []
    elif dataset == 'klarna':
        weblist = glob.glob(os.path.join(DATA_HOME, '*'))
    elif dataset == 'weir':
        weblist = glob.glob(os.path.join(DATA_HOME, field, '*'))
    elif dataset == 'news':
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
        elif dataset == 'news':
            website_name = website_path.split('/')[-1]
        
        logger.info('-'*200)
        logger.info(website_name)
        logger.info(os.path.join(OUTPUT_HOME, PATTERN, field, website_name) + f'_{PATTERN}.json')
        if (website_name in filter_website) or (not overwrite and os.path.exists(os.path.join(OUTPUT_HOME, PATTERN, field, website_name) + f'_{PATTERN}.json')):
            continue

        if dataset in ['swde', 'ex_swde', 'ds1', 'weir', 'news']:
            webpage_list = glob.glob(os.path.join(website_path, '*'))
        elif dataset == 'klarna':
            webpage_list = glob.glob(os.path.join(website_path, '*', 'source.html'))
        xpath_rule = {}
        html_list = []
        if dataset in ['swde', 'ex_swde', 'weir', 'news']:
            sorted(webpage_list)
            long_website = False
            random.shuffle(webpage_list)
            for html_page in webpage_list[:num_seed_website]:
                with open(html_page, 'r', encoding='utf8', errors='ignore') as f:
                    # For skipping
                    html = f.read()
                    # if num_tokens_from_string(simplify_html(html), "cl100k_base") < 10000:
                    #     long_website = True
                    #     break
                    html_list.append(html)
            if long_website:
                logger.info('SKIP')
                continue
        elif dataset == 'ds1':
            with open(website_path, 'r', errors='ignore') as f:
                html_list.append(f.read())
        elif dataset == 'klarna':
            sorted(webpage_list)
            if len(webpage_list) <= num_seed_website:
                logger.info(f'Website {website_name} contains less or equal than {num_seed_website} pages.')
                continue
            long_website = False
            for html_page in webpage_list[:num_seed_website]:
                with open(html_page, 'r') as f:
                    html = f.read()
                    html_list.append(html)
                    if model == 'ChatGPT':
                        if num_tokens_from_string(simplify_html(html), "cl100k_base") > 15000:
                            logger.info(f'Website {website_name} contains HTML longer than 15000.')
                            long_website = True
                            break
                    elif model in ['deepseek','GPT4','phi']:
                        if num_tokens_from_string(simplify_html(html), "cl100k_base") > 31000:
                            logger.info(f'Website {website_name} contains HTML longer than 32000.')
                            long_website = True
                            break
            if long_website:
                continue

        for item in SCHEMA[field]:
            logger.info('-'*150)
            instruction = f"{prompt[field]['meta']} {prompt[field][item]} {prompt['meta']}"
            logger.info(instruction)
                
            try:
                xpath_rule[item] = xe.rule_synthesis(website_name, html_list, instruction, max_token=max_token)
            except Exception as e:
                logger.error(traceback.format_exc()) 
                logger.error(e)
            logger.info(f'{field} {item} end.')
            #xpath_rule[item] = xe.rule_synthesis_cul(website_name, html_list, instruction, max_token=max_token)
        with open(os.path.join(OUTPUT_HOME, PATTERN, field, website_name) + f'_{PATTERN}.json', 'w', errors='ignore') as f:
            json.dump(xpath_rule, f, indent=4)