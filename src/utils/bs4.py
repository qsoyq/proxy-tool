from bs4 import BeautifulSoup as Soup, Tag


def select_one_by(document: Soup | Tag, selector: str):
    try:
        cur = document
        for query in selector.split(">"):
            tag = cur.select_one(query)
            if tag is None:
                return None
            cur = tag
        return cur
    except AttributeError:
        return None
