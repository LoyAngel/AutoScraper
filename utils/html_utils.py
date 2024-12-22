import sys
sys.setrecursionlimit(3000)
from bs4 import BeautifulSoup
from lxml import etree
from lxml.etree import _Element
import bs4
import tiktoken
import difflib
import re

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
        tree = etree.HTML(html_content)
        #print(xpath)
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
        print(f"Error: {e}")
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
    [s.extract() for s in soup('head')]
    for tag in soup.find_all():
        try:
            new_attrs = {}
            for attr in reserve_attrs:
                if attr in tag.attrs.keys(): 
                    new_attrs = {attr: tag.attrs[attr]}
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

def get_pure_text(html):
    # soup = BeautifulSoup(html, 'html.parser')
    # text = soup.get_text().replace('\t',' ')
    # text = '\n'.join([line for line in text.split('\n') if line.strip() != ''])
    # text = ' '.join([line for line in text.split(' ') if line.strip() != ''])
    tree = etree.HTML(html)
    i = 0
    element_text_dict = {}
    for element in tree.iter():
        # get element_texts
        element_text = ""
        if element.text:
            element_text += element.text
        if element.tail:
            element_text += element.tail
        element_text = re.sub(r'\s+', '', element_text)
        if element_text:
            element_text_dict[str(i)] = element_text
        else:
            continue
        i += 1

    return str(element_text_dict)

def simplify_html_inverted(value: str, index: int, html: str) -> str:
    LEVEL_NUM = 4 # the number of ancestor levels to consider
    if value == "":
        return ""

    i = 0
    element_select = None
    tree = etree.HTML(html)
    for element in tree.iter():
        # get element_texts
        element_text = ""
        if element.text:
            element_text += element.text
        if element.tail:
            element_text += element.tail

        element_text = re.sub(r'\s+', '', element_text)
        if not element_text:
            continue
        if i == index:
            element_select = element
            break
        i += 1
    
    ancestor = element_select
    if ancestor is not None:
        for _ in range(LEVEL_NUM):
            if ancestor.getparent() is not None:
                ancestor = ancestor.getparent()
            else:
                break

    simplified_html = etree.tostring(ancestor, pretty_print=True, encoding='unicode')
    
    return simplified_html


if __name__ == '__main__':
    import requests
    with open('/mnt/data122/harryhuang/swde/sourceCode/university/university-collegeboard(2000)/0435.htm', 'r') as f:
        html_content = f.read()
        html_content = simplify_html(html_content)
        #print(html_content)
        #print(simplify_html(html))
        #print(len(simplify_html(html)))
    xpath = "//h3[text()='Type of School']"
    print(find_common_ancestor(html_content, xpath))
    abs_xpath = get_absolute_xpath(html_content, xpath)
    print(find_common_ancestor(html_content, abs_xpath))