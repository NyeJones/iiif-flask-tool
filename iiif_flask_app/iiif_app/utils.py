import os
import re
import json
import logging
import warnings
import string
import nh3
from collections import defaultdict
from natsort import natsorted
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from flask import request, url_for


#ensure file is run from correct directory in editor
os.chdir(os.path.dirname(__file__))
#filter to ignore unnecessary Beautiful Soup warning
warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)

def remove_punctuation(s):
    """
    Removes punctuation characters from a string and replaces them with spaces.

    Parameters:
    s (str): The input string from which punctuation characters will be removed.

    Returns:
    str: The input string with punctuation characters replaced by spaces.
    """
    translation_table = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    return s.translate(translation_table)

def clean_text(text):
    """
    Clean the input text by replacing newlines and carriage returns with spaces,
    replacing specific characters, removing extra spaces, and trimming leading/trailing whitespaces.

    Parameters:
    - text (str): The input text to be cleaned.

    Returns:
    str: The cleaned text.
    """
    text = text.replace('\n', ' ').replace('\r', '')
    text = re.sub("ʼ", "'", text)
    text = re.sub(' +', ' ', text)
    clean_text = text.strip()
    return clean_text

def extract_strings_and_integers(data):
    """
    Recursively extracts strings and integers from nested dictionaries and lists.

    Parameters:
    - data: A dictionary or list containing nested data.

    Yields:
    - Strings and integers extracted from the nested data.
    
    Note:
    This function recursively traverses the input data structure and yields strings and integers
    encountered along the way. It skips over other data types.
    """
    if isinstance(data, dict):
        for value in data.values():
            yield from extract_strings_and_integers(value)
    elif isinstance(data, list):
        for item in data:
            yield from extract_strings_and_integers(item)
    elif isinstance(data, str) or isinstance(data, int):
        yield str(data)


def extract_html_text(value):
    """
    Extracts text content from HTML using Beautiful Soup,
    performs data sanitation using the nh3 library,
    handles input errors and logs them.

    Parameters:
    - value (str, list or dict): The content to extract text from.

    Returns:
    - str: Extracted text content from HTML.

    Notes:
    This function takes HTML content as input and uses nh3 and Beautiful Soup to sanitise and extract the text content.
    If the input contains lists or dictionaries, it extracts strings and integers recursively using the function
    `extract_strings_and_integers` (from the values in dictionary), 
    converts them to a comma-separated string, and then parses any resulting HTML content. 
    Any errors encountered during the extraction process are logged using the logging module.
    """
    try:
        if isinstance(value, (list, str, dict)):
            value = list(extract_strings_and_integers(value))
            value = ', '.join(value)
        clean_value = nh3.clean(value)
        soup = BeautifulSoup(clean_value, 'html.parser')
        text = soup.get_text()
        return text
    except Exception as e:
        # Log the error for debugging purposes
        logging.error(f'Error in extract_html_text: {e}', exc_info=True)
        return None


def custom_get(param='', default_value='*'):
    """
    Get a parameter value from request.args, sanitize the value,
    and ensure it's a non-empty string. If parameter is None or fails validation,
    return the default value of an asterisk (wildcard).

    Parameters:
    - param: the parameter to retrieve.
    - default_value: the default value if the parameter is not empty

    Returns:
    - str: The sanitized value of the parameter or the default value.
    - Error message if exception occurs
    """
    try:
        response = request.args.get(param)
        if isinstance(response, str) and response.strip():
            clean_response = nh3.clean(response)
            return clean_response
        elif response is None:
            return default_value
        else:
            raise ValueError('Response for custom_get invalid, must be either non-empty string or None')
    except Exception as e:
        # Log the error for debugging purposes
        logging.error(f'Error in custom_get: {e}', exc_info=True)
        return None

def custom_get_int(param):
    """
    Get a parameter value from request.args and ensure it's a valid integer.
    If the parameter is missing, None is returned.
    
    Parameters:
    - param: the request param to retrieve from request.args.

    Returns:
    - int or None: The sanitized integer value of the parameter, or None if the 
      parameter is missing or not convertible to an integer.
    """
    try:
        response = request.args.get(param, 1, type=int)
        if isinstance(response, int):
            return response
        else:
            raise ValueError('Response for custom_get_int invalid,  must be integer')
    except Exception as e:
        # Log the error for debugging purposes
        logging.error(f'Error in custom_get: {e}', exc_info=True)
        return None


def get_metadata_value(metadata, label_pattern):
    """
    Get the value from metadata based on whether label contains a regex,
    use for extracting different parts of metadata for 'language', 'date', etc.
    
    Each item in metadata should be a dictionary with keys of 'label' and 'value'.
    Check 'label' value for regex and if there extract 'value' value.

    Parameters:
    - metadata (list): list of metadata entries.
    - label_pattern (str): regex pattern to match the label.

    Returns
    - str: the value corresponding to matched label pattern or 'N/A' if any exception occurs.
    """
    try:
        for item in metadata:
            if item['label'] is not None:
                label_str = str(item['label'])
                if re.search(label_pattern, label_str, re.IGNORECASE):
                        return item['value']
        return 'N/A'
    except Exception as e:
        print(f"An error occurred: {e}")
        return 'N/A'

def safe_json_get(json_object, key, index=None, default=None):
    """
    Safely extract values from JSON object, return None if error in extraction.

    Parameters:
    - json_object (dict): The JSON object.
    - key (str): The key to extract from the JSON object.
    - index (int, optional): index to access list elements (if applicable).
    - default: default value to return if key is not found.

    Returns:
    - item at index number from list if that is JSON key value.
    - item if no index number specified.
    - default of None and logged if error in extracting JSON
    """
    if index is not None:
        try:
            return json_object.get(key)[index]
        except Exception as e:
            # Log the error for debugging purposes
            logging.error(f'Error in safe_json_get: {e}', exc_info=True)
            return default
    else:
        try:
            return json_object.get(key)
        except Exception as e:
            # Log the error for debugging purposes
            logging.error(f'Error in safe_json_get: {e}', exc_info=True)
            return default

def json_value_extract_clean(json_value):
    """
    Fully extract, sanitise and clean extracted json value.
    If value is None return 'N/A'.
    Use extract_html_text to sanitise with nh3 and fully extract any html.
    Use clean_text to standardise aspects of spacing and formatting.
    Returns clean text string of json_value or 'N/A'.
    """
    if json_value is None:
        return 'N/A'
    else:
        json_value_extract = extract_html_text(json_value)
        if json_value_extract:
            json_value_clean = clean_text(json_value_extract)
            return json_value_clean
        else:
            return 'N/A'

def sidebar_counts(results, json_key, item_key, item_names, query_params):
    """
    Count occurrences of items in search results for sidebar links.
    Sanitise all parameters to make sure they are correct type.
    Count different values of json_key e.g. "json_repository" in results.
    If all words of a value appear in another value, e.g. 'Persian' in 'Arabic and Persian', add the count of that item to its count.
    For each link, update the query parameters from previous search to incorporate a sidebar value.
    Use nh3 to validate the links, deal with ampersand encoding.
    Get current count for the sidebar value from counts done above.
    Create dictionary for each sidebar item with count and link to update the current results
    incorporating that item and append to list for all links for a particular sidebar value e.g. 'Language'.

    Parameters:
    - results (list): List of dictionaries for each result.
    - json_key (str): JSON key to extract sidebar type from each result, e.g. 'json_repository'.
    - item_key (str): Key to identify items in the sidebar, e.g. 'repository'.
    - item_names (list): (set processed) list of item names for counting.
    - query_params (dict): Dictionary of query parameters with counts from previous results.

    Returns:
    - list: Sorted list of dictionaries containing item details for sidebar links for relevant sidebar category.
    """
    
    #validate input parameter data types
    if not isinstance(results, list):
        raise ValueError('Results must be a list of dictionaries')
    if not isinstance(item_names, (list, set)):
        raise ValueError('Unique repositories must be a list or set')
    if not isinstance(query_params, dict):
        raise ValueError('Query parameters must be provided as a dictionary')
    if not isinstance(json_key, str):
        raise ValueError('json_key must be a string')
    if not isinstance(item_key, str):
        raise ValueError('item_key must be a string')

    #do initial count of items for json_key
    item_counts = {}
    for result in results:
        item = result.get(json_key)
        #remove question marks so 'Morocco?' is treated same as 'Morocco' in sidebar links, for example
        item = item.replace('?', '')
        if len(item) > 70:
            item = item[:70] + '...'
        if item in item_counts:
            item_counts[item] += 1
        else:
            item_counts[item] = 1
    
    #create cumulative_counts dictionary
    cumulative_counts = defaultdict(int)

    #tokenize each key in item counts
    for key in item_counts:
        key_words = key.replace('-', ' ')
        key_words = set(remove_punctuation(key).split())
        #for each tokenized key loop through all other keys, tokenized
        for other_key, count in item_counts.items():
            other_key_words = other_key.replace('-', ' ')
            #if key is different to other key but all words in other key present in key add other key count to count for the key
            #this adds counts for substring keys to the key counts
            if key != other_key and all(word in remove_punctuation(other_key_words).split() for word in key_words):
                cumulative_counts[key] += count

    #add on substring counts for each key
    for key in item_counts:
        item_counts[key] += cumulative_counts[key]

    #create links for sidebar item
    item_links = []
    items_done = []
    #for each item in links get the query parameters and update item key with item name
    #so repository would be updated to a repository name
    for item_name in item_names:
        #first remove duplicate items in different order: e.g. 'Fes, Morocco' and 'Morocco, Fes'
        #convert to set and add to done list, if already in done list don't create sidebar link
        item_set = set(remove_punctuation(item_name).split())
        if item_set in items_done:
            continue
        else:
            items_done.append(item_set)
            query_params_copy = query_params.copy()
            query_params_copy[item_key] = item_name

            #use this to create a link for updated results incorporating that item name, sanitised with nh3
            link = url_for('results', **query_params_copy)
            clean_link = nh3.clean(link)
            clean_link = link.replace('&amp;', '&')
            
            #if item name is long reduce length to find relevant count in item_counts
            if len(item_name) > 70:
                item_name = item_name[:70] + '...'
            item_count = item_counts.get(item_name, 0)
            #append data for each item to list of item data for sidebar
            item_links.append({
                item_key: item_name,
                'search_link': clean_link,
                'count': item_count
            })

    #return sorted list of item links for relevant sidebar section
    sorted_item_links = sorted(item_links, key=lambda x: x['count'], reverse=True)
    return sorted_item_links