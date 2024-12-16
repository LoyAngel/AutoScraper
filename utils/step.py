from bs4 import BeautifulSoup,NavigableString,Tag,Comment
from copy import copy
from utils.html_utils import *

def calculate_dom_depth(element, depth=0):
    """
    Recursively calculates the depth of the DOM tree.
    Args:
    - element: BeautifulSoup object or tag to calculate depth for.
    - depth: current depth of recursion (initially 0).

    Returns:
    - Maximum depth of the DOM tree from the current element.
    """
    if not element.contents:
        return depth
    else:
        return max(calculate_dom_depth(child, depth + 1) for child in element.children if hasattr(child, 'contents'))


def domlm_parse(soup:Tag, max_len):
    """
    Parse the DOM tree to get the subtree with a maximum number of tokens.
    Args:
    - soup: BeautifulSoup object to parse.
    - max_len: Maximum number of tokens to keep in the subtree.

    Returns:
    - List of strings representing the subtree.
    """
    subtree = []
    while True:
        delete = False
        dup_soup = copy(soup)
        descendants = list(dup_soup.descendants)
        for ele in reversed(descendants):
            if isinstance(ele, Tag):
                #print(len(str(dup_soup)))
                # if len(str(dup_soup)) > max_len: 
                token_num = num_tokens_from_string(str(dup_soup), "cl100k_base")
                if token_num > max_len:
                    ele.decompose()
                    delete = True
                else:
                    # print('='*50)
                    # print(dup_soup.prettify())
                    subtree.append(str(dup_soup))
                    break
        if not delete:
            break
        ancester = list(ele.parents)
        for a, b in zip(list(dup_soup.descendants), list(soup.descendants)):
            # print('a:',a)
            if ele == a:
                break
            if isinstance(b, Tag):
                # print('-'*50)
                # print(a)
                # print([a.parent == x for x in ancester])
                if a.parent in ancester:
                    pass
                else:
                    # print(b)
                    b.decompose()
    # print('=='*15)
    # print(soup)
    return subtree

if __name__ == '__main__':
    from html_utils import *
    html_content = """<html>
<body>
    <div>
        <ul>
            <p>Keep this paragraph</p>
            <p>Delete this paragraph</p>
        </ul>
        <ul>
            <li>Delete this item</li>
            <li>Delete this item too</li>
        </ul>
    </div>
    <div>
        <p>Delete all in this div</p>
        <ul>
            <p>Keep this paragraph</p>
            <p>Delete this paragraph</p>
        </ul>
        <ul>
            <li>Delete this item</li>
            <li>Delete this item too</li>
        </ul>
    </div>
    <ul>
        <p>Keep this paragraph</p>
        <p>Delete this paragraph</p>
    </ul>
    <ul>
        <li>Delete this item</li>
        <li>Delete this item too</li>
    </ul>
</body>
</html>
    """
    html_content = simplify_html(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    subtree = domlm_parse(soup, 100)
    print(subtree)