import sys
sys.setrecursionlimit(3000)
from bs4 import BeautifulSoup
from lxml import etree
from lxml.etree import _Element
import bs4
import tiktoken
import difflib
import re
import logging

logger = logging.getLogger('crawler')
class StepTree:
    def __init__(self, html, step_len = 5000, len_func = len):
        self.soup = BeautifulSoup(html)
        self.step_len = step_len
        self.len_func = len_func

    def __iter__(self):
        if self.len_func(str(self.soup)) < self.step_len:
            yield 

def find_common_ancestor(html_content:str, xpath:str):
    try:
        parser = etree.HTMLParser(recover=False)
        tree = etree.HTML(html_content.encode('utf-8'), parser=parser) # type: ignore
        #logger.info(xpath)
        xpath = xpath.replace('::text()','::*')
        xpath = xpath.replace('/text()','/*')
        nodes = tree.xpath(xpath)
        # get the ancestors of each node
        ancestors_list = [set(n.xpath('ancestor::*')) for n in nodes]

        if not ancestors_list:
            return html_content
        # find the common ancestors
        common_ancestors = set.intersection(*ancestors_list)

        # choose the nearest common ancestor (the one with the longest path)
        nearest_common_ancestor = max(common_ancestors, key=lambda x: x.getroottree().getpath(x).count('/'))
        ancestor_string = etree.tostring(nearest_common_ancestor, pretty_print=True, encoding='unicode')
        return ancestor_string
    except:
        return html_content

def get_absolute_xpath(html, xpath):
    """
    Given an HTML string and an XPath expression, returns the absolute XPath of the element.
    :param html: HTML content as a string
    :param xpath: XPath expression as a string
    :return: Absolute XPath string or None if not found
    """
    try:
        tree = etree.HTML(html)
        node = tree.xpath(xpath)
        if not node:
            return None
        if isinstance(node, list):
            node = node[0]
        return build_absolute_xpath(node)
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def build_absolute_xpath(node):
    """
    Constructs an absolute XPath expression for a given node.
    :param node: A lxml node for which to build the XPath
    :return: A string representing the absolute XPath to the node
    """
    parts = []
    while node is not None and isinstance(node, _Element) and node.tag != 'html':
        parent = node.getparent()
        siblings = [sib for sib in parent.iterchildren() if sib.tag == node.tag]
        count = siblings.index(node) + 1
        parts.insert(0, f"{node.tag}[{count}]")
        node = parent
    return '/html/' + '/'.join(parts)

def simplify_html(html, reserve_attrs = ['class', 'id']):
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup(text=lambda text: isinstance(text, bs4.Comment)):
        element.extract()
    
    [s.extract() for s in soup('script')]
    [s.extract() for s in soup('style')]
    [s.extract() for s in soup('input')]
    head = soup.find('head')
    if head:
        [s.extract() for s in head(text=lambda text: text is None)]

    for tag in soup.find_all():
        try:
            new_attrs = {}
            for attr in reserve_attrs:
                if tag.get(attr):
                    new_attrs[attr] = tag.get(attr)
            tag.attrs = new_attrs
        except:
            pass
    html = str(soup)
    
    html = '\n'.join([line for line in html.split('\n') if line.strip() != ''])

    return html

def parse_accessibility_tree(html, indent='\t'):
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup(text=lambda text: isinstance(text, bs4.Comment)):
        element.extract()
    [s.extract() for s in soup('script')]
    [s.extract() for s in soup('style')]

    accessibility_tree = ''
    for node in soup.children:
        if isinstance(node, bs4.NavigableString):
            pass
        else:
            parse_accessibility_tree()

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    #print(string)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def get_pure_text(html: str) -> str:
    # soup = BeautifulSoup(html, 'html.parser')
    # text = soup.get_text().replace('\t',' ')
    # text = '\n'.join([line for line in text.split('\n') if line.strip() != ''])
    # text = ' '.join([line for line in text.split(' ') if line.strip() != ''])
    tree = etree.HTML(html.encode('utf-8')) # type: ignore
    element_text_list = []
    for element in tree.iter():
        # get element_texts
        element_text = ""
        if element.text:
            element_text += element.text
        if element.tail:
            element_text += element.tail
        element_text = re.sub(r'\s+', '', element_text)
        if element_text:
            element_text_list.append(element_text)
    return str(element_text_list)

def simplify_html_inverted(value: str, neighbors: list, html: str) -> str:
    LEVEL_NUM = 4 # the number of ancestor levels to consider
    COMBINED_NUM = 2 
    def similarity_cal(text1, text2) -> float:
        # calculate the similarity between two strings
        seq = difflib.SequenceMatcher(None, text1, text2)
        return seq.ratio()
    
    if value == "" and any(neighbors) == False:
        return html

    neighbors.insert(0, value)
    total_value = ''.join(neighbors)


    # extract the text of each element in the html, excluding the text of its children
    element_text_list = []
    element_neighbors_text_list = []
    tree = etree.HTML(html.encode('utf-8')) # type: ignore
    for element_to_find in tree.iter():
        # get element_texts
        element_text = ""
        if element_to_find.text:
            element_text += element_to_find.text
        if element_to_find.tail:
            element_text += element_to_find.tail
        element_text = re.sub(r'\s+', '', element_text)
        if element_text:
            element_text_list.append(element_text)
        
    for i in range(len(element_text_list)):
        element_neighbors_text = ""
        if i != 0:
            element_neighbors_text += element_text_list[i - 1]
        element_neighbors_text += element_text_list[i]
        if i != len(element_text_list) - 1:
            element_neighbors_text += element_text_list[i + 1]
        element_neighbors_text_list.append(element_neighbors_text)



    # calculate the similarity between the given text and the text of each element element_neighbors_text_list[i])
    similarities = [similarity_cal(value, element_text_list[i]) * 0.6 + similarity_cal(total_value, element_neighbors_text_list[i]) * 0.4
                    for i in range(len(element_text_list))]
    sorted_similarities = sorted(similarities, reverse=True)

    simplified_html = ""
    for index in range(COMBINED_NUM):
        similar_element_index = similarities.index(sorted_similarities[index])
        similar_element_text = element_text_list[similar_element_index]
        try:
            logger.info(f'similar_element{index}:{similar_element_text}')
        except:
            pass
        # find the common ancestor of the most similar element
        # soup = BeautifulSoup(html, 'html.parser')
        # element = soup.find(string=similar_element_text)
        i = 0
        element = None
        for element_to_find in tree.iter():
            element_text = ""
            if element_to_find.text:
                element_text += element_to_find.text
            if element_to_find.tail:
                element_text += element_to_find.tail
            element_text = re.sub(r'\s+', '', element_text)
            if not element_text:
                continue
            if i == similar_element_index:
                element = element_to_find
                break
            i += 1
        
        ancestor = element
        if ancestor is not None:
            for _ in range(LEVEL_NUM):
                if ancestor.getparent() is not None:
                    ancestor = ancestor.getparent()
                else:
                    break
        
        to_be_added = etree.tostring(ancestor, pretty_print=True, encoding='unicode')
        if to_be_added in simplified_html:
            continue
        if simplified_html in to_be_added:
            simplified_html = to_be_added
            continue
        simplified_html += to_be_added
    
    return simplified_html


if __name__ == '__main__':
    import requests
    with open('inverted_html.txt', 'r') as f:
        html_content = f.read()
        html_content = simplify_html(html_content)
        #print(html_content)
        #print(simplify_html(html))
        #print(len(simplify_html(html)))
    xpath = "//div[@id='nameAddress']/h5[1]/text() | //div[@id='nameAddress']/h5[2]/a[@class='addressLink']/text() | //div[@id='nameAddress']/h5[2]/a[@class='addressLink'][2]/text() | //div[@id='nameAddress']/h5[2]/a[@class='addressLink'][3]/text()"
    value = "12305 Mayfield Rd. (Murray Hill Rd.) Cleveland, OH 44106"
    print(find_common_ancestor(html_content, xpath))
    while True:
        new_html_content = find_common_ancestor(html_content, xpath)
        new_html_content_clear = re.sub(r'\s', '', new_html_content)

        is_step_back = False
        values = re.split(r'\s+', value)
        values = [re.sub(r'\s', '', v) for v in values]
        for value in values:
            if value not in new_html_content_clear:
                is_step_back = True
                break
        if is_step_back and new_html_content != html_content:
            xpath += '/..'
        else:
            print(xpath)
            break