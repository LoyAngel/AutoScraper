import json, re
from lxml import etree, html
from utils.html_utils import simplify_html, find_common_ancestor, get_pure_text, html_element_text_similarity_cal
from utils.step import domlm_parse
from bs4 import BeautifulSoup

role_prompt = '''Suppose you're a web parser that is good at reading and understanding the HTML code and can give clear executable code on the brower.'''
crawler_prompt = '''Please read the following HTML code, and then return an Xpath that can recognize the element in the HTML matching the instruction below. 

Instruction: {0}

Here're some hints:
1. Do not output the xpath with exact value or element appears in the HTML.
2. Do not output the xpath that indicate multi node with different value. It would be appreciate to use more @class to identify different node that may share the same xpath expression.
3. If the HTML code doesn't contain the suitable information match the instruction, keep the xpath and value attrs blank.
4. Avoid using some string function such as 'substring()' and 'normalize-space()' to normalize the text in the node.
Please output in the following Json format:
{{
    "thought": "", # a brief thought of how to confirm the value and generate the xpath
    "value": "", # the value extracted from the HTML that match the instruction, if there is no data, keep it blank
    "xpath": "" # a workable xpath to extract the value in the HTML
}}

Please think step by step as following:
0. Find the target value suiting the instruction above first, and make it be the value in the following json.
1. Find generalizable text attributes related to the values specified in the instruction using class names, text(), and descendant element content. Construct a base XPath from these attributes, ensuring it is as unique as possible. 
2. Because the unique element has been located by relative positioning, the next step is to extend the base Xpath using absolute positioning. Try to use the '[NUM]' to locate the element.'text()' and 'following-sibling' could aslo be used in the xpath. Ensure the final XPath selector returns a unique element.
3. Write the result in the Json format as above.

Here's the HTML code:
```
{1}
```
'''

crawler_wr_prompt = '''Please read the following HTML code, and then return an Xpath that can recognize the element in the HTML matching the instruction below. 

Instruction: {0}
The element value: {1}

Here're some hints:
1. Do not output the xpath with exact value or element appears in the HTML.
2. Do not output the xpath that indicate multi node with different value. It would be appreciate to use more @class to identify different node that may share the same xpath expression.
3. If the HTML code doesn't contain the suitable information match the instruction, keep the xpath and value attrs blank.
4. Avoid using some string function such as 'substring()' and 'normalize-space()' to normalize the text in the node.
Please output in the following Json format:
{{
    "thought": "", # a brief thought of how to confirm the value and generate the xpath
    "xpath": "" # a workable xpath to extract the value in the HTML
}}
Here's the HTML code:
```
{2}
```
'''

stepback_prompt = '''Your main task is to judge whether the following HTML code contains all the expected value, which is recognized beforehand.
Instruction: {0}
And here's the value: {1}
The HTML code is as follow:
```
{2}
```

Please output your judgement in the following Json format:
{{
    "thought": "", # a brief thinking about whether the HTML code contains expected value
    "judgement": "" # whether the HTML code contains all extracted value. Return yes/no directly.
}}
'''

judgement_prompt = '''Your main task is to judge whether the extracted value is consistent with the expected value, which is recognized beforehand. Please pay attention for the following case:
    1) If the extracted result contains some elements that is not in expected value, or contains empty value, it is not consistent.
    2) Differences in punctuations, symbols or formatting are acceptable.
    3) The following cases are considered matching: Type differences ; Repeated values ; Values with prefix.

The extracted value is: {0}
The expected value is: {1}

Please output your judgement in the following Json format:
{{
    "thought": "", # a brief thinking about whether the extracted value is consistent with the expected value
    "judgement": "" # return yes/no directly
}}
'''

synthesis_prompt = '''You're a perfect discriminator which is good at HTML understanding as well. Following the instruction, there are some action sequence written from several HTML and the corresponding result extracted from several HTML. Please choose one that can be best potentially adapted to the same extraction task on other webpage in the same websites.
Please evaluate each action sequence based on these criteria, rating them on a scale of 1-10 (integer):
Accuracy: Whether the value in the "extracted result" matches the content required by the instructions.
Generalizability: The preference for flexible selectors (e.g., [@class='st.']) over rigid ones (e.g., [text()='st.']), indicating better adaptability.
Simplicity: Shorter expressions are preferred over longer ones, provided the output remains stable and accurate.

Here are the instruction of the task:
Instructions: {0}

Pay Attention:
The action sequences are not alternative paths - all steps must be executed in sequence to retrieve the value.

The action sequences and the corresponding extracted results with different sequence on different webpage are as follow:
{1}


Please rate every action sequence in the following Json format:
{{
    "thought": "" # brief explanation of your selection rationale.
    "rate": "" # list of ratings for each sequence, formatted as "[[accuracy1, generalizability1, robustness1], ...]", a null action sequence should be rated by "[0, 0, 0]".
}}
'''

inverted_prompt = '''You're a perfect text reader which is good at understanding the text content. Please recognize the best value following the instruction below.

Instruction: {0}
Please output in the following Json format:
{{
    "thought": "", # a brief thought of how to confirm the value
    "value": "" # the value extracted from the text content that match the instruction
}}

Here's the text content:
```
{1}
```

'''
class StepbackExtraCrawler:
    def __init__(self,
                 simplify=True,
                 verbose=True,
                 api=None,
                 error_max_times=15):

        if api == None:
            raise ValueError("No api has been assigned!!")
        self.api = api
        self.is_simplify = simplify
        self.verbose = verbose
        self.error_max_times = error_max_times

    def request_parse(self, 
                      query: str,
                      keys: list[str] = []) -> dict[str, str]:
        """A safe and reliable call to LLMs, which confirm that the output can be parsed by json.loads().

        Args:
            query (str): the query to prompt the LLM
            html (str): the HTML text for 

        Returns:
            str: a dict parsed from the output of LLM
        """
        pattern = r'\{.*?\}'
        target = False
        for _ in range(self.error_max_times):
            response = self.api(query)
            matches = re.findall(pattern, response, re.DOTALL)
            try:
                for match in matches:
                    res = json.loads(match) # type: ignore
                    for key in keys:
                        assert res[key]
                    target = True
                if target:
                    break
            except:
                pass
        if target:
            #print(res)
            return res
        else:
            return {key:"" for key in keys}
        
    def generate_sequence_html(self,
                          instruction: str,
                          html_content: str,
                          ground_truth=None):
        LOOP_TIMES = 3

        action_sequence = []

        for index in range(LOOP_TIMES):
            if ground_truth:
                query = f'{role_prompt}{crawler_wr_prompt.format(instruction, ground_truth, html_content)}'
                res = self.request_parse(query, ['thought', 'xpath'])
            else:
                query = f'{role_prompt}\n{crawler_prompt.format(instruction, html_content)}'
                with open('crawler.txt', mode='w+', encoding='utf8') as f:
                    f.write(query)
                res = self.request_parse(query, ['thought', 'value', 'xpath'])
        
            results = self.extract_with_xpath(html_content, res['xpath'])
            xpath = res['xpath']
            value = ground_truth if ground_truth else res['value']
        
            
            try:
                print('-' * 50)
                print(value)
                print(results)
                print(xpath)
            except:
                pass

            if value == '':
                return action_sequence

            query = f'{role_prompt}\n{judgement_prompt.format(str(results), value)}'
            res = self.request_parse(query, ['thought', 'judgement'])
            if res['judgement'].lower() == 'yes':
                action_sequence.append(xpath)
                return action_sequence

            if index == LOOP_TIMES - 1: # Last loop doesn't need to stepback
                break
            
            # Stepback
            while True:
                new_html_content = find_common_ancestor(html_content, xpath)
                new_html_content_clear = re.sub(r'\s', '', new_html_content)
                # query = f'{role_prompt}\n{stepback_prompt.format(instruction, value, new_html_content)}'
                # res = self.request_parse(query, ['thought', 'judgement'])
                # if res['judgement'] == 'yes' or new_html_content == html_content:
                #     action_sequence.append(xpath)
                #     break
                # else:
                #     xpath += '/..'

                is_step_back = False
                values = value.split(',') if ',' in value else [value]
                values = [re.sub(r'\s', '', value) for value in values]
                for value in values:
                    if value not in new_html_content_clear:
                        is_step_back = True
                        break
                if is_step_back and new_html_content != html_content:
                    xpath += '/..'
                else:
                    action_sequence.append(xpath)
                    break
                    
            html_content = new_html_content

        return action_sequence

    def generate_sequence(self, instruction, html_content, ground_truth = None, max_token=8000):
        if self.is_simplify:
            html_content = simplify_html(html_content)
        #print(html_content)
        soup = BeautifulSoup(html_content, 'html.parser')
        subtree_list = domlm_parse(soup, max_token)
        print('Page split:', len(subtree_list))
        rule_list = []
        for sub_html in subtree_list:
            page_rule = self.generate_sequence_html(instruction, sub_html, ground_truth)
            rule_list.append(page_rule)
        
        if len(subtree_list) > 1:
            valid_answer = False
            for rule in rule_list:
                if rule != []:
                    valid_answer = True
            if not valid_answer:
                return []
            extract_result = []
            for rule in rule_list:
                sub_extract_result = {'rule':rule}
                sub_extract_result['extracted result'] = self.extract_with_sequence(html_content, rule)
                extract_result.append(sub_extract_result)
            print(json.dumps(extract_result, ensure_ascii=False, indent=4))
            return self.rate_and_perferred(instruction, extract_result, rule_list)
        else:
            return rule_list[0]
        
    def rate_and_perferred(self, instruction, extract_result, rule_list):
        ACCURACY_SCORE_WEIGHT = 0.4
        GENERALIZABILITY_SCORE_WEIGHT = 0.2
        ACTION_COUNT_SCORE_WEIGHT = 0.15
        AVERAGE_LENGTH_SCORE_WEIGHT = 0.15
        ROBUSTNESS_SCORE_WEIGHT = 0.1

        def local_rate():
            # action count score
            action_count_list = [len(rule) for rule in rule_list]
            action_count_max, action_count_min = max(action_count_list), min(action_count_list)
            if action_count_max == action_count_min:
                action_count_score_list = [10] * len(action_count_list)
            else:
                action_count_score_list = [
                    int(10 - 9 * (action_count_score - action_count_min) / (action_count_max - action_count_min)) 
                    for action_count_score in action_count_list
                ]

            # average length score
            average_length_list = []
            for rule in rule_list:
                rule_total_length = 0
                for xpath in rule:
                    rule_total_length += len(xpath)
                if rule_total_length == 0:
                    average_length_list.append(0)
                else:
                    average_length_list.append(rule_total_length / len(rule))
            average_length_max, average_length_min = max(average_length_list), min(average_length_list)
            if average_length_max == average_length_min:
                average_length_score_list = [10] * len(average_length_list)
            else:
                average_length_score_list = [
                    int(10 - 9 * (average_length_score - average_length_min) / (average_length_max - average_length_min))
                    for average_length_score in average_length_list
                ]

            return smooth_scores(action_count_score_list), smooth_scores(average_length_score_list)

        def smooth_scores(score_list):
            '''
            Smooth the scores process like LLM does
            '''
            sorted_indices = sorted(range(len(score_list)), key=lambda k: score_list[k])
            sorted_scores = [score_list[i] for i in sorted_indices]
            length = len(score_list)
            
            # Generate smoothed scores
            if length < 10:
                smoothed_scores = list(range(10, 10 - length, -1))
            else:
                smoothed_scores = [10 - int(10 * i / length) for i in range(length)]
            
            # Assign smoothed scores, ensuring equal original scores get the same smoothed score
            final_scores = [0] * length
            last_score, last_smoothed = None, None
            
            for i, index in enumerate(sorted_indices):
                if sorted_scores[i] == last_score:
                    final_scores[index] = last_smoothed
                else:
                    last_score = sorted_scores[i]
                    last_smoothed = smoothed_scores[i]
                    final_scores[index] = last_smoothed
            
            return final_scores
    
        query = synthesis_prompt.format(instruction, json.dumps(extract_result, indent=4))
        res = self.request_parse(query, ['thought', 'rate'])
        llm_rate = eval(res['rate']) if isinstance(res['rate'], str) else res['rate']
        action_count_score_list, average_length_score_list = local_rate()
        
        total_score_list = []
        final_index = 0
        try:
            for index in range(len(rule_list)):
                total_score = action_count_score_list[index] * ACTION_COUNT_SCORE_WEIGHT + \
                                average_length_score_list[index] * AVERAGE_LENGTH_SCORE_WEIGHT + \
                                llm_rate[index][0] * ACCURACY_SCORE_WEIGHT + \
                                llm_rate[index][1] * GENERALIZABILITY_SCORE_WEIGHT + \
                                llm_rate[index][2] * ROBUSTNESS_SCORE_WEIGHT
                total_score_list.append(total_score)
            print(total_score_list)
            final_index = total_score_list.index(max(total_score_list))
        except:
            import traceback
            traceback.print_exc()
            print(llm_rate)

        print(f"Final index: {final_index}")
        return rule_list[final_index]

    def rule_synthesis(self, 
                       website_name: str,
                       seed_html_set: list[str], 
                       instruction: str, 
                       ground_truth = None,
                       max_token = 8000,
                       per_page_repeat_time=1):
        rule_list = []

        # Collect a rule from each seed webpage
        if ground_truth:
            for html_content, gt in zip(seed_html_set, ground_truth):
                page_rule = self.generate_sequence(instruction, html_content, gt, max_token=max_token)
                rule_list.append(page_rule)
        else:
            for html_content in seed_html_set:
                inverted_html_content = self.inverted_search(html_content, instruction)
                page_rule = self.generate_sequence(instruction, inverted_html_content, max_token=max_token)
                rule_list.append(page_rule)

        #rule_list = list(set(rule_list))
        try:
            print(rule_list)
        except:
            pass

        if len(seed_html_set) > 1:
            valid_answer = False
            for rule in rule_list:
                if rule != []:
                    valid_answer = True
            if not valid_answer:
                return []
            extract_result = []
            for rule in rule_list:
                sub_extract_result = {'rule':rule, 'extracted result':[]}
                for html_content in seed_html_set:
                    sub_extract_result['extracted result'].append(self.extract_with_sequence(html_content, rule))
                extract_result.append(sub_extract_result)
            
            try:
                print('+' * 100)
                print(f"Systhesis rule for the website {website_name}")
                print(json.dumps(extract_result, ensure_ascii=False, indent=4))
            except:
                pass

            return self.rate_and_perferred(instruction, extract_result, rule_list)
        else:
            return rule_list[0]
        
    def extract_with_xpath(self, 
                           html_content:str, 
                           xpath:str) -> list[str]:
        """Xpath Parser

        Args:
            html_content (str): text of HTML
            xpath (str): the string of xpath

        Returns:
            list[str]: result extracted by xpath
        """
        if self.is_simplify:
            html_content = simplify_html(html_content)
        try:
            if xpath.strip():
                ele = etree.HTML(html_content) # type: ignore
                return [item.strip() if isinstance(item, str) else item.text.strip() for item in ele.xpath(xpath)]
            else:
                return []
        except:
            return []
        
    def extract_with_sequence(self,
                              html_content:str,
                              sequence:str):
        if self.is_simplify:
            html_content = simplify_html(html_content)
        if sequence == []:
            return []
        else:
            tot_len = len(sequence)
            for index, xpath in enumerate(sequence):
                if index != tot_len - 1:
                    try:
                        html_content = find_common_ancestor(html_content, xpath)
                    except:
                        pass
                else:
                    return self.extract_with_xpath(html_content, xpath)
    
    def inverted_search(self, html_content:str, instruction:str):
        if self.is_simplify:
            html_content = simplify_html(html_content)
        query = f'{role_prompt}\n{inverted_prompt.format(instruction, get_pure_text(html_content))}'
        res = self.request_parse(query, ['thought', 'value'])
        print(res)
        value = res['value']

        return html_element_text_similarity_cal(value, html_content)



       
        