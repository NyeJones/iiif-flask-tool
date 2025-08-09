import os
import re
import json
import logging
import warnings
import string
import nh3
import hashlib
from unidecode import unidecode
from collections import defaultdict
from natsort import natsorted
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from flask import request, url_for
from whoosh.searching import Results, Searcher
from whoosh.sorting import FieldFacet
from whoosh.query import And, Term, Every


#ensure file is run from correct directory in editor
os.chdir(os.path.dirname(__file__))
#filter to ignore unnecessary Beautiful Soup warning
warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)

#configure logger for this module
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def make_cache_key_excluding_page():
    """
    Generates a consistent cache key for the search results route, excluding the 'page' parameter.
    
    Returns:
    str: A unique cache key string based on the request's arguments (except 'page').
    """
    args = {k: v for k, v in request.args.items() if k != 'page'}
    return 'results:' + hashlib.md5(json.dumps(args, sort_keys=True).encode()).hexdigest()

def remove_punctuation(s):
    """
    Removes punctuation characters from a string and replaces them with spaces.

    Parameters:
    s (str): The input string from which punctuation characters will be removed.

    Returns:
    str: The input string with punctuation characters replaced by spaces.

    Raises:
    ValueError: If the input is not a string.
    """
    if not isinstance(s, str):
        raise ValueError(f"Expected string, got {type(s)}")
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

    Raises:
    ValueError: If the input is not a string.
    """
    if not isinstance(text, str):
        raise ValueError(f"Expected string for text, got {type(text)}")
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
    - list: Extracted text content from HTML as a list of strings, empty list if error occurs.

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
        #log the main error for the function with the input value
        logger.error(f'Error in extract_html_text for value: {value} ({type(value)}). Error: {e}', exc_info=True)
        return []

def custom_get(param='', default_value='*'):
    """
    Get a parameter value from request.args, sanitize the value,
    and ensure it's a non-empty string. If parameter is None or fails validation,
    return the default value of an asterisk (wildcard). 

    In case of validation failure, raise a `ValueError`, log the error, 
    and return the default value.

    Parameters:
    - param: the parameter to retrieve.
    - default_value: the default value if the parameter is not empty

    Returns:
    - str: The sanitized value of the parameter or the default value.
    """
    try:
        response = request.args.get(param)
        #checking if non-empty string
        if isinstance(response, str) and response.strip():
            clean_response = nh3.clean(response)
            return clean_response
        elif response is None or response == "":
            return default_value
        else:
            raise ValueError(f"Invalid value for '{param}': must be a non-empty string or None.")
    except Exception as e:
        logger.error(f"Error in custom_get for parameter '{param}': {e}", exc_info=True)
        return default_value

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
            raise ValueError(f"Response for {param} must be an integer")
    except Exception as e:
        logger.error(f"Error in custom_get_int for parameter '{param}': {e}", exc_info=True)
        return None


def get_metadata_value(metadata, label_pattern):
    """
    Get values from metadata list where the label matches a regex pattern.
    This can be used to extract specific metadata values like 'language', 'date', etc.

    Each item in the metadata list must be a dictionary with non-empty 'label' and 'value' keys. 
    Items without these keys or with empty values will be skipped.
    If this is true then check whether the 'label' value matches the provided regex pattern. 
    If it does the corresponding 'value' value is added to the result list.

    Parameters:
    - metadata (list): A list of dictionaries containing metadata entries. Each dictionary
      needs a 'label' key and 'value' key to be considered.
    - label_pattern (str): The regex pattern to match against the 'label' value.

    Returns:
    - list: A list of values corresponding to matched patterns. If no match is found,
      or if any exception occurs, it returns ['N/A'].
    """
    try:
        if not isinstance(metadata, list):
            raise ValueError("Metadata must be a list of dictionaries.")
        metadata_vals = []
        for item in metadata:
            #check item is dictionary then for 'label' and 'value' keys
            if isinstance(item, dict) and item.get('label') and item.get('value'):
                #check 'label' value against regex
                label_str = str(item['label'])
                #if there is a match return the value of 'value' key
                if re.search(label_pattern, label_str, re.IGNORECASE):
                        metadata_vals.append(item['value'])
        return metadata_vals if metadata_vals else ['N/A']
    except Exception as e:
        logger.error(f"Error in get_metadata_value: {e}", exc_info=True)
        return ['N/A']

def safe_json_get(json_object, key, index=None, default=None, logging=True):
    """
    Safely extract values from a JSON-like dictionary, returning a default value in case of errors.
    A 'TypeError' will be raised internally if 'index' is provided but the value is not a list.
    Unexpected errors logged for debugging purposes if logging is True, but key errors are not logged.
    
    Parameters:
    - json_object: The JSON-like dictionary.
    - key: The key string to look for in the dictionary.
    - index: Index number to access list elements (if applicable).
    - default: The default value to return if the key is not found or an error occurs.

    Returns:
    - The item at the specified index from the list if 'index' is provided.
    - The value associated with the key if 'index' is not provided.
    - The 'default' value if the key is not found or an error occurs.
    """
    try:
        #get the value associated with the key
        value = json_object[key]
        #access the index if it's a list
        if index is not None:
            if isinstance(value, list):
                return value[index]
            #raise type error if value not a list
            else:
                raise TypeError(f"Expected a list for key '{key}', got {type(value)}")
        return value
    except KeyError:
        #do not log key errors as they are expected
        return default
    except Exception as e:
        #log unexpected exceptions at the error level if logging is True
        if logging:
            logger.error(f"Unexpected error in safe_json_get: {e}", exc_info=True)
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
    - json_value (list): A list of JSON values (which can be strings, lists, or dictionaries) 
      to extract and clean.

    Returns:
    - list: A list of cleaned text values extracted from the JSON value, or ['N/A'] if the content 
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

def sidebar_counts(query, searcher, query_params, json_key, item_key):
    """
    Builds a sidebar section with links and counts based on a given facet of search results.

    This function uses a Whoosh search query and searcher to group search results
    by a specified JSON field (facet), counts and normalizes the field values, and 
    generates search links that filter results by each unique value. It returns 
    a sorted list of dictionaries suitable for rendering sidebar filter sections.

    Parameters:
    - query (whoosh.query.Query): A Whoosh query object (e.g. And, Every).
    - searcher (whoosh.searching.Searcher): A Whoosh Searcher used to run the query.
    - query_params (dict): Dictionary of existing query parameters for URL construction.
    - json_key (str): The name of the field to facet/group by in search results (e.g. 'json_repository').
    - item_key (str): The label for the item in the sidebar (e.g. 'repository', 'language').

    Returns:
    list of dicts: Each dictionary represents a sidebar item and contains:
        - item_key (str): the original item name (unsanitized).
        - search_link (str): URL to search with this item as a filter.
        - count (int): number of matching results for the item.

    Raises error if validation checks not passed.
    """
    
    #validate input parameter data
    if not isinstance(item_key, str):
        raise ValueError('item_key for sidebar section must be a string')
    if not isinstance(query_params, dict):
        raise TypeError('Query parameters must be provided as a dictionary')
    if not isinstance(json_key, str):
        raise ValueError('json_key for result extraction must be a string')
    if not isinstance(query, (And, Every)):
        raise TypeError('Expected a Whoosh query object (And or Every) for "query"')
    if not isinstance(searcher, Searcher):
        raise TypeError('Expected a Whoosh Searcher object for "searcher"')
    
    #create a facet object using the field name (json_key)
    facet = FieldFacet(json_key)
    #execute search with faceting enabled (groupedby)
    results = searcher.search(query, groupedby=facet)
    #extract the grouped results
    facet_groups = results.groups(json_key)
    #validate that the grouping returned a dictionary
    if not isinstance(facet_groups, dict):
        raise ValueError(f"facet_groups for sidebar must be dictionary")

    #create a new dictionary to hold facet keys after splitting multi-value entries
    expanded_groups = {}

    #iterate over each facet key and its list of matching doc_ids
    for raw_key, doc_ids in facet_groups.items():
        #if the facet key is a string containing a '|' separator,
        #it represents multiple values in one field
        if isinstance(raw_key, str) and '|' in raw_key:
            #split into individual parts, trimming whitespace around each part
            parts = [part.strip() for part in raw_key.split('|')]
            #for each separate value, add the same doc_ids to that value's group
            for part in parts:
                expanded_groups.setdefault(part, []).extend(doc_ids)
        else:
            #for keys without '|', just add them directly to the expanded dictionary
            expanded_groups.setdefault(raw_key, []).extend(doc_ids)

    #replace the original facet_groups with the expanded version
    facet_groups = expanded_groups

    #normalize and count items (case and punctuation insensitive)
    #e.g. "repository-A", "repository a" will be treated as the same
    merged_keys = {}
    #extract raw keys which are the unprocessed items from each category
    #and doc_ids which are the matching documents for that key
    for raw_key, doc_ids in facet_groups.items():
        #skip non-string keys – some fields might be missing or malformed
        if not isinstance(raw_key, str):
            continue
        #normalise the key to make lower case and remove punctuation
        norm_key = unidecode(remove_punctuation(raw_key)).lower()
        #if normalized key already exists in merged_keys, 
        #increment its count by length of doc ids
        if norm_key in merged_keys:
            merged_keys[norm_key][0] += len(doc_ids)
        #if normalized key doesn't exist, store count and original raw label as tuple
        else:
            merged_keys[norm_key] = [len(doc_ids), raw_key]

    #create a rolled count dictionary for finding subsets
    #e.g. "Arabic" will contain the count for "Judaeo-Arabic", 
    #which will also be counted as a separate category
    rolled_counts = {}
    for norm_key in merged_keys:
        #convert each normalized key into a set of words
        norm_set = set(norm_key.split())
        #start with the count from this key
        base_count = merged_keys[norm_key][0]
        #compare against every other key in the list
        for other_key in merged_keys:
            if norm_key == other_key:
                continue
            other_set = set(other_key.split())
            #if all words in this key are contained in another, consider it a subset
            if norm_set.issubset(other_set):
                #add count for subset key to base count
                base_count += merged_keys[other_key][0]
        #use the original (raw) key for display purposes in the sidebar
        raw_key = merged_keys[norm_key][1]
        rolled_counts[raw_key] = base_count


    #build sidebar list: one dictionary per item with name, link, and count
    sidebar = []
    for item, count in rolled_counts.items():
        #skip items with no results
        if count < 1:
            continue
        #create a copy of current query parameters and update with the current item
        query_copy = query_params.copy()
        query_copy[item_key] = item
        try:
            #generate a new URL for the results page filtered by this item
            link = url_for('results', **query_copy)
        except Exception as e:
            #raise error if url generation fails
            raise ValueError(f"Failed to generate URL for query params: {query_copy}, error: {e}")
        #sanitize link and correct HTML encoding
        clean_link = nh3.clean(link)
        clean_link = link.replace('&amp;', '&')
        #append the item to the sidebar with its name, link, and result count
        sidebar.append({
            item_key: item,
            'search_link': clean_link,
            'count': count
        })

    #sort sidebar items by descending count, then alphabetically
    sidebar.sort(key=lambda x: (-x['count'], x[item_key].lower()))   
    return sidebar