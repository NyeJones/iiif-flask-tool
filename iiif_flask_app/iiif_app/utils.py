import os
import re
import json
import logging
import warnings
import string
import nh3
from unidecode import unidecode
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
    performs data sanitation using the nh3 library, string clean-up with function
    handles input errors and logs them.

    Parameters:
    - value (str, list, or dict): The content to extract text from.

    Returns:
    - list: Extracted text content from HTML as a list of strings.

    Notes:
    This function takes HTML content as input and uses nh3, string cleaning and Beautiful Soup to sanitise and extract the text content.
    If the input contains lists or dictionaries, it extracts strings and integers recursively using the function
    `extract_strings_and_integers` (from the values in dictionary), and parses any resulting HTML content. 
    Any errors encountered during the extraction process are logged using the logging module.
    """
    try:
        #extract strings and integers recursively to list format
        if isinstance(value, (list, str, dict)):
            value_list = list(extract_strings_and_integers(value))
        #create an empty list to store cleaned and extracted text
        cleaned_text_list = []
        #loop through the extracted values
        for item in value_list:
            #clean each item using nh3
            nh3_value = nh3.clean(item)
            #string clean up/standardisation
            clean_value = clean_text(nh3_value)          
            #parse the cleaned HTML using BeautifulSoup
            soup = BeautifulSoup(clean_value, 'html.parser')      
            #extract text from the parsed HTML
            text = soup.get_text()
            #remove leading and trailing commas and semicolons
            text = text.strip(';,')
            #if not a blank string, add text to list
            if text.strip():
                cleaned_text_list.append(text)
        return cleaned_text_list
    except Exception as e:
        #log any errors for debugging purposes
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
        #checking if non-empty string
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
    Get values from metadata where the label matches a regex pattern.
    This can be used to extract specific metadata like 'language', 'date', etc.

    Each item in the metadata should be a dictionary with keys 'label' and 'value'.
    The function checks if the 'label' matches the provided regex pattern, and if it does,
    the corresponding 'value' is added to the result list.

    Parameters:
    - metadata (list): A list of dictionaries containing metadata entries. Each dictionary
      needs a 'label' and 'value' key to be considered.
    - label_pattern (str): The regex pattern to match against the 'label' field.

    Returns:
    - list: A list of values corresponding to matched label patterns. If no match is found,
      or if any exception occurs, it returns ['N/A'].
    """
    try:
        metadata_vals = []
        for item in metadata:
            if item.get('label') and item.get('value'):
                label_str = str(item['label'])
                if re.search(label_pattern, label_str, re.IGNORECASE):
                        metadata_vals.append(item['value'])
        if not metadata_vals:
            return ['N/A']
        else:
            return metadata_vals
    except Exception as e:
        print(f"An error occurred: {e}")
        return ['N/A']

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
    Extract, sanitize, and clean JSON values.

    This function handles various types of JSON values (e.g., strings, lists, or dictionaries) 
    and ensures the extraction of text content while sanitizing any HTML. It uses the 
    `extract_html_text` function to clean and standardize the content. If the input is 
    None, empty, or cannot be processed, it returns ['N/A']. Otherwise, it returns a cleaned 
    and fully extracted list of strings.

    Parameters:
    - json_value_ls (list): A list of JSON values (which can be strings, lists, or dictionaries) 
      to extract and clean.

    Returns:
    - list: A list of cleaned text values extracted from the JSON, or ['N/A'] if the content 
            is invalid, empty, or cannot be processed.
    """
    #if the json_value is None, return ['N/A'] as a fallback
    if not json_value:
        return ['N/A']
    else:
        json_value_extract_ls = []
        #use extract_html_text to sanitize and extract any HTML content into a list of strings
        json_value_extract = extract_html_text(json_value)
        json_value_extract_ls.extend(json_value_extract)
        #if the extracted value contains valid content, return it
        if json_value_extract_ls:
            return json_value_extract_ls
        else:
            #if the extraction returns no content, return ['N/A'] as a fallback
            return ['N/A']

def sidebar_counts(results, query_params, index_lists, json_key, item_key):
    """
    Generates a sorted list of links for a sidebar section based on the provided input parameters.

    This function takes a list of results and generates links for each unique item 
    in a specified index list. It counts how many times each item appears in the 
    results, sanitizes the item names (removing punctuation and handling case 
    variations), and generates a clean URL for each item. The links are sorted by 
    the item count in descending order and alphabetically by item name in case 
    of ties in count.

    Parameters:
    - results (list): List of dictionaries for content of each result.
    - json_key (str): JSON key to extract sidebar type from each result, e.g. 'json_repository'.
    - index_lists (dict): A dictionary containing lists of items for each index category, accessed via item_key.
    - item_key (str): Key to identify items in the sidebar, e.g. 'repository'.
    - query_params (dict): Dictionary of query parameters from previous results.

    Returns:
    list: A list of dictionaries containing the following keys for each item for each sidebar link:
        - `item_key`: The item name.
        - `search_link`: A URL to search for that item from within current results.
        - `count`: The number of results matching the item.
    """
    
    #validate input parameter data types
    if not isinstance(results, list):
        raise ValueError('Results must be a list of dictionaries')
    if not isinstance(index_lists, dict):
        raise ValueError('Index lists must be a list')
    if not isinstance(query_params, dict):
        raise ValueError('Query parameters must be provided as a dictionary')
    if not isinstance(json_key, str):
        raise ValueError('json_key must be a string')
    if not isinstance(item_key, str):
        raise ValueError('item_key must be a string')

    #access correct index list for specific sidebar section
    #contains all valid categories for that sidebar section
    index_list = index_lists[item_key]

    #this section removes duplicates from the index list
    #includes removing duplicate items in different order: e.g. 'Fes, Morocco' and 'Morocco, Fes'
    items_done = []
    unique_index_list = []
    for ind_item in index_list:
        # Normalize with unidecode, including diacritical marks, and remove punctuation for comparison purposes
        normalized_item = unidecode(ind_item)
        item_set = set(remove_punctuation(normalized_item).split())
        #if item set already found in items done don't include
        if item_set in items_done:
            continue
        #if item set not found in items done, add item to unique index list
        #and also items done list
        else:
            unique_index_list.append(ind_item)
            items_done.append(item_set)
            
    #this section creates a list of index item links
    item_links = []
    #iterate through each index item and the results for relevant sidebar section
    #count occurrences of index item in results
    for ind_item in unique_index_list:
        #establish count for item
        item_count = 0
        #remove question marks and dashes and normalize with unidecode for purpose of comparison
        ind_item = ind_item.replace('?', '')
        param_item = ind_item.replace('-', ' ')
        param_item = unidecode(param_item)
        #copy query string and make a new query string with index item
        #under key for relevant sidebar section
        query_params_copy = query_params.copy()
        query_params_copy[item_key] = ind_item
        
        #count occurrence of index item in all results for relevant section
        #iterate through results and extract relevant content
        for result in results:
            res_item = result.get(json_key)
            #remove question marks and dashes and normalize with unidecode for purpose of comparison
            res_item = res_item.replace('?', '').replace('-', ' ')
            res_item = unidecode(res_item)
            #check index item words against results words, if all the same add 1 to index item count
            #this takes into account instances like 'Fes, Morocco' and 'Morocco, Fes'
            #where same item has different order
            if all(word in remove_punctuation(res_item).split() for word in remove_punctuation(param_item).split()):
                item_count += 1

        #create link for index item using updated query string
        link = url_for('results', **query_params_copy)
        #sanitize link and reformat ampersand
        clean_link = nh3.clean(link)
        clean_link = link.replace('&amp;', '&')
        
        #if item count is above zero add dictionary for item to item links list
        #this will be used for that index item within relevant sidebar section
        #includes link for updated query, count and item text
        if item_count > 0:
            item_links.append({
                item_key: ind_item,
                'search_link': clean_link,
                'count': item_count
            })
        
    #sort by count and alphabetically by item text if counts match
    sorted_item_links = sorted(item_links, key=lambda x: (-x['count'], x[item_key].lower()))
    #return all links for the sidebar section
    return sorted_item_links