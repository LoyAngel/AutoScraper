
weir_prompt = {
    'meta': 'It\'s worth noticing that the candidate attribute values are the non-empty strings contained in text nodes in the corresponding DOM tree, and one page may contain multiple distinct values that correspond to an attribute.',
    'book': {
        'meta': 'Here\'s a webpage on detail information of a book.',
        'STRING : AUTHOR': "Please extract the author of the book.",
        'STRING : BINDING': "Please extract the binding of the book.",
        'STRING : PUBLISHER': "Please extract the publisher of the book.",
        'STRING : TITLE': "Please extract the title of the book."
    },
    'finance' : {
        'meta': 'Here\'s a webpage on detail information of given stock data.',
        'NUMBER : 52wk high': "Please extract the highest price of the stock in the past 52 weeks.",
        'NUMBER : 52wk low': "Please extract the lowest price of the stock in the past 52 weeks.",
        'NUMBER : high': "Please extract the highest price of lastest trading day.",
        'NUMBER : low': "Please extract the lowest price of lastest trading day.",
        'NUMBER : value': "Please extract the current value of the stock."
    },
    'soccer' : {
        'meta': 'Here\'s a webpage on detail information of a soccer player.',
        'DATE : birthdate': "Please extract the birthdate of the soccer player.",
        'SPACE : height': "Please extract the height of the soccer player.",
        'STRING : national_team': "Please extract the national_team of the soccer player.",
        'STRING : position': "Please extract the position of the soccer player."
    },
    'videogame' : {
        'meta': 'Here\'s a webpage on detail information of a videogame.',
        'STRING : developer': "Please extract the developer of the videogame.",
        'STRING : esrb': "Please extract the esrb rating of the videogame, and not contain the explanation of the rating.",
        'STRING : genre': "Please extract the genre/category of the videogame.",
        'STRING : publisher': "Please extract the 'publisher' of the videogame."
    }
}