import os
import re
import json
import logging
import warnings
import string
import nh3
from collections import defaultdict
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
#flask imports
from flask_talisman import Talisman
from flask_paginate import Pagination, get_page_args
from flask import Flask, request, render_template, redirect, url_for
from flask_caching import Cache
#whoosh search engine imports
from whoosh.writing import AsyncWriter
from whoosh.analysis import CharsetFilter, StandardAnalyzer
from whoosh.support.charset import accent_map
from whoosh.fields import Schema, TEXT, STORED, ID
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import Term, And, Regex
from whoosh.searching import Results
#app specific forms and config file imported
from forms import SearchForm
from config import Config

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
    - results (list): List of Whoosh search results.
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
            clean_link = clean_link.replace('&amp;', '&')
            
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

#create a Flask app 
app = Flask(__name__)

#initialize flask-cache to increase app effiency
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

#create route to static folder for css and javascript files
app.static_folder = 'static'
#import config data from config file, including security key, into app
app.config.from_object(Config)
# Set SESSION_COOKIE_SAMESITE to 'Lax'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

#get config data for site from file
#iiif image api
background_image = app.config['BACKGROUND_IMAGE']
#sanitisation of html link for image
background_image = extract_html_text(background_image)
#iiif image api
intro_image = app.config['INTRO_IMAGE']
#sanitisation of html link for image
intro_image = extract_html_text(intro_image)

#various text items to fill parts of the site
main_title = app.config['MAIN_TITLE']
caption_text = app.config['CAPTION_TEXT']
long_intro = app.config['LONG_INTRO']
about_data = app.config['ABOUT']
proj_team_data = app.config['PROJECT_TEAM']
ad_board_data = app.config['ADVISORY_BOARD']

#dictionary of footer names and urls
footer_data = app.config['FOOTER']
#dictionary of repositories and identifiers
repositories = app.config['REPOSITORIES']
#list of base urls for validation in Mirador viewer and thumbnails
#more base urls can be added to the list in the config file, following pattern there
base_urls = app.config ['BASE_URLS']

#sanitise url for links in footer data
for key, value in footer_data.items():
    clean_value = extract_html_text(value)
    footer_data[key] = clean_value

#Content Security Policy (CSP) directives - rules that define the allowed sources for various types of content
#style needs to be 'unsafe-inline' for mirador generated inline style elements to work
csp = {
    'default-src': ['\'self\'', 'https://maxcdn.bootstrapcdn.com', 'https://ajax.googleapis.com'],
    'connect-src': ['\'self\''],
    'img-src': ['\'self\'', 'data:'],
    'script-src': ['\'self\'', 'https://ajax.googleapis.com', 'https://maxcdn.bootstrapcdn.com', 'https://unpkg.com'],
    'style-src': ['\'self\'', 'https://maxcdn.bootstrapcdn.com', '\'unsafe-inline\''],
    'script-src-elem': ['\'self\'', 'https://unpkg.com', 'https://maxcdn.bootstrapcdn.com', 'https://ajax.googleapis.com', '\'unsafe-inline\''],
    # Add more CSP directives as needed
}

#add base urls for different repositories to csp for validation
csp['connect-src'].extend(base_urls)
csp['img-src'].extend(base_urls)

#initialize Flask-Talisman with CSP configuration
#Talisman also includes HSTS, X-content type, x-frame and cookie settings for app security
#default settings followed, see github for flask-talisman
talisman = Talisman(app, content_security_policy=csp)

#initialise analyzer for Whoosh search engine, essentially a tokenizer with filters.
#no stop words and conversion of accented characters to standardised in our case.
no_stop_analyzer = StandardAnalyzer(stoplist=None) | CharsetFilter(accent_map)

#define the schema for the search index
#treat fields as text, store in the index, add analyser initialised above, make sortable.
schema = Schema(
    iiif_path=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    json_label=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    json_date=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    json_language=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    json_material=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    json_description=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    json_repository=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    json_thumbnail=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
    )

# create or open the index file using the schema created above
if not os.path.exists('index'):
    os.mkdir('index')
ix = create_in('index', schema)

#specify location for input files directory
files_directory = 'files'

#loop through files directory and extract json file of each iiif manifest
all_json_data = []
for root, dirs, files in os.walk(files_directory):
    for file in files:
        if file.endswith('json'):
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as json_file:
                json_data = json.load(json_file)
                all_json_data.append(json_data)

#index the file paths in the 'files' directory
#use asyncwriter imported above to avoid concurrency locks on writing to index
writer = AsyncWriter(ix)

#check for duplicate iiif records and empty id fields
seen_ids = set()
unique_json_records = []
#loop through records
for json_record in all_json_data:
    #get iiif id from record
    record_id = safe_json_get(json_record, '@id')
    #use function to sanitise data with nh3 library
    record_id = extract_html_text(record_id)
    #if None or duplicate print message
    if record_id is None:
        print('Empty ID field in IIIF record')
    elif record_id in seen_ids:
        print(f'Duplicate record, one added: {record_id}')
    #if ok add to json data and add id to seen ids
    else:
        unique_json_records.append(json_record)
        seen_ids.add(record_id)

#loop through each iiif manifest json file
#use functions to extract and prepare data
for item in unique_json_records:
    
    #extract unique iiif id and sanitise
    json_id = safe_json_get(item, '@id')
    json_id = extract_html_text(json_id)

    #for other values extract, sanitise and clean data, return 'N/A' if None
    json_label = safe_json_get(item, 'label')
    json_label = json_value_extract_clean(json_label)
    
    json_description = safe_json_get(item, 'description')
    json_description = json_value_extract_clean(json_description)

    #create default value of 'N/A' for additional metadata categories
    json_date = 'N/A'
    json_language = 'N/A'
    json_material = 'N/A'

    #use function to extract iiif metadata if there
    metadata = safe_json_get(item, 'metadata')
    if metadata:
        
        #if metadata present we need to use a function to extract any subcategories
        #these are based on broad, yet reliable, regex substrings, such as 'date', 'language', 'material'
        #this is because metadata categories are decided on by institutions and
        #not standardised as part of the iiif schema
        #we also use our json_value_extract_clean to sanitise, fully extract and clean json values
        #if category not there make 'N/A'

        json_date = get_metadata_value(metadata, r'date')
        json_date = json_value_extract_clean(json_date)

        json_language = get_metadata_value(metadata, r'language')
        json_language = json_value_extract_clean(json_language)

        json_material = get_metadata_value(metadata, r'material')
        json_material = json_value_extract_clean(json_material)

    #create default value of 'N/A' for repository
    json_repository = 'N/A'

    #repository for each item identified by substring within manifest id
    #loop through repositories imported from config
    for key, value in repositories.items():
        #if repository key found in id then give it repository value
        if re.search(key, json_id):
            json_repository = value
            break

    #use Beautiful Soup function to extract thumbnail image id
    #images are well nested so need a few uses of function, return None if no image id
    first_sequence = safe_json_get(item, 'sequences', index=0)
    first_canvas = safe_json_get(first_sequence, 'canvases', index=0)
    first_image = safe_json_get(first_canvas, 'images', index=0)
    resource = safe_json_get(first_image, 'resource')
    service = safe_json_get(resource, 'service')
    if service:
        iiif_image_url = safe_json_get(service, '@id')
    else:
        iiif_image_url = safe_json_get(resource, '@id')        
    #perform data sanitisation on url
    iiif_image_url = extract_html_text(iiif_image_url)

    #suffix patterns to remove from image id if there
    suffix_remove_patterns = [r'/full/.*/0/.*jpg']
    #new suffix to add to the end of all thumbnail urls, to get correct size for thumbnail
    new_suffix = '/full/!200,200/0/default.jpg'

    #loop through patterns and remove if there
    for pattern in suffix_remove_patterns:
        #if pattern present replace with new suffix in image url
        if re.search(pattern, iiif_image_url):
            json_thumbnail = re.sub(pattern, new_suffix, iiif_image_url)
            break
        #if pattern not present add new suffix to the end of image url
        else:
            json_thumbnail = iiif_image_url + new_suffix

    #add data from the manifest to the Whoosh index to make it searchable in the site
    writer.add_document(
        iiif_path=json_id, 
        json_label=json_label,
        json_date=json_date,
        json_language=json_language,
        json_material=json_material,
        json_description=json_description,
        json_repository=json_repository,
        json_thumbnail=json_thumbnail,
        )
#commit data for all manifests to the Whoosh index
writer.commit()

#open the Whoosh search index for searching with all manifest data included
ix = open_dir('index')

#this section contains the app routes for the creation of the website
#and rendering html templates
#templates stored in 'templates' folder alongside the file for this script
#cache used for routes that do not change due to user input

@app.context_processor
def main():
    """
    Allows form variables invoked by SearchForm to be accessible across app
    #SearchForm method allows us to utilise csrf protection on user searches
    
    Returns:
    - A dictionary containing the 'form' variable, representing the SearchForm instance.
    """
    form = SearchForm()
    return dict(form=form, footer_data=footer_data)

@app.route("/")
@cache.cached(timeout=86400)
def home():
    """Render home page html template."""
    return render_template('home.html', main_title=main_title, caption_text=caption_text, 
        long_intro=long_intro, background_image=background_image, intro_image=intro_image)

@app.route('/about')
@cache.cached(timeout=86400)
def about():
    """Render about page html template."""
    return render_template('about.html', about_data=about_data)

@app.route('/contact')
@cache.cached(timeout=86400)
def contact():
    """Render contact page html template."""
    return render_template('contact.html', proj_team_data=proj_team_data, ad_board_data=ad_board_data)

@app.route('/search', methods=['POST'])
def search():
    """
    Handle search form submission for the site.
    Gets query from form and normalizes.
    Preserves existing query parameters from the url when redirecting.
    Uses SearchForm from function above to ensure csrf protection on user searches.

    Returns:
    - Response: Redirects to the 'results' route with query parameters.
    - If query is blank or invalid returns invalid query template.  
    """
    
    #use function to extract previous queries from url and perform data sanitation
    #default to wildcard if no query
    repository = custom_get(param='repository')
    language = custom_get(param='language')
    material = custom_get(param='material')

    #check for query sent by form
    query = None
    form = SearchForm(request.form)
    #validate query for security
    if form.validate_on_submit():
        #check if query is blank and string
        query = form.searched.data.strip()
        if query is not None and isinstance(query, str):
            #clean up query
            query = re.sub(r'\W+\s*', ' ', query).strip()
            #return query to results route with url parameters extracted above
            return redirect(url_for('results', query=query, repository=repository, language=language, material=material))
    
    #return invalid query template if invalid or blank
    invalid_msg = f'Invalid or blank query, please search again.'
    return render_template('invalid-query.html', invalid_msg=invalid_msg)

@app.route('/results')
def results():
    """
    Displays search results including those of previously searched parameters.

    Returns:
    - Rendered template with search results paginated.
    - Includes results, previous queries from url, pagination, count and sidebar parameters.
    """

    #use function to extract previous queries from url and perform data sanitation
    #default to wildcard if no query
    user_query = custom_get(param='query')
    repository = custom_get(param='repository')
    language = custom_get(param='language')
    material = custom_get(param='material')


    #put queries in dictionary for use below in sidebar function
    query_params = {'query': user_query, 'repository': repository, 'language': language, 'material': material}

    #use Whoosh search index for search using query parameters
    with ix.searcher() as searcher:
        
        #use function to safely extract page number from query string
        page = custom_get_int('page')
        #create additional page variables
        per_page = 20
        offset = (page - 1) * per_page
        
        #creates Whoosh parser for appropriate fields using search index
        parser = MultifieldParser(['iiif_path', 'json_label', 'json_date', 'json_description', 'json_thumbnail'], ix.schema)
        #formulates a search query using parser and user query
        search_query = parser.parse(f'*{user_query}*')

        #filters added to this list from query string items
        filters = []

        #for each query string item create a parser specific to appropriate index field
        #parse index for matches and add results to filters
        #do for all sidebar sections and append to filters list
        repository_parser = QueryParser('json_repository', schema=ix.schema)
        repository_query = repository_parser.parse(repository)
        filters.append(repository_query)
        language_parser = QueryParser('json_language', schema=ix.schema)
        language_query = language_parser.parse(language)
        filters.append(language_query)
        material_parser = QueryParser('json_material', schema=ix.schema)
        material_query = material_parser.parse(material)
        filters.append(material_query)

        #create combined query from filters and user query then search Whoosh index
        search_query = And([search_query] + filters)
        results = searcher.search(search_query, limit=None, sortedby='iiif_path')
        #convert results to list of dictionaries
        results = [dict(result) for result in results]

        #total number of results
        total = len(results)
        #subset of results for appropriate page
        results_subset = results[offset: offset + per_page]
        #create pagination using Flask Paginate library, 
        pagination = Pagination(page=page, per_page=per_page, total=total, record_name='results', css_framework='foundation')

        #get sets of values for each sidebar query parameter from results
        unique_repositories = set(result.get('json_repository') for result in results)
        unique_languages = set(result.get('json_language') for result in results)
        unique_materials = set(result.get('json_material') for result in results)

        #remove question marks so 'Paper?' is treated same as 'Paper' in sidebar links, for example
        unique_repositories = set(repository.replace('?', '') for repository in unique_repositories)
        unique_languages = set(language.replace('?', '') for language in unique_languages)
        unique_materials = set(material.replace('?', '') for material in unique_materials)

        #use function to get sidebar links for results page
        #these will redirect to another results page composed of any existing queries and new query including sidebar value choice
        repository_links = sidebar_counts(results=results, item_names=unique_repositories, query_params=query_params, 
            json_key='json_repository', item_key='repository')
        language_links = sidebar_counts(results=results, item_names=unique_languages, query_params=query_params,
            json_key='json_language', item_key='language')
        material_links = sidebar_counts(results=results, item_names=unique_materials, query_params=query_params,
            json_key='json_material', item_key='material')

        #returns rendered template with results subset for page, query string parameters, pagination, 
        #sidebar link data and total count of results 
        return render_template("results.html", results=results_subset, query_params=query_params, pagination=pagination,
            repository_links=repository_links, language_links=language_links, material_links=material_links, count=total)


@app.route('/index')
def list_files():
    """
    Displays rendered template of all index files.

    Returns:
    - Rendered template with index files paginated.
    - Includes results, wildcard query to show all results, pagination, count and sidebar parameters.
    """

    #use Whoosh search index to generate all files
    with ix.searcher() as searcher:

        #creates Whoosh parser for appropriate fields using search index
        parser = MultifieldParser(['iiif_path', 'json_label', 'json_date', 'json_language', 'json_material',
            'json_description', 'json_repository', 'json_thumbnail'], ix.schema)
        #as we are locating all files, wildcard search used on all fields
        query = parser.parse('*')

        #use function to safely extract page number from query string
        page = custom_get_int('page')
        #create additional page variables
        per_page = 20
        offset = (page - 1) * per_page
        
        
        #cache key for the complete results set
        cache_key_all_results = 'all_results'
        all_results = cache.get(cache_key_all_results)
        if all_results is None:
            #perform search of index to generate all results using parser generated above
            all_results = searcher.search(query, limit=None, sortedby='iiif_path')
            #convert results to list of dictionaries for caching
            all_results = [dict(result) for result in all_results]
            #cache the results for future use
            cache.set(cache_key_all_results, json.dumps(all_results), timeout=86400)
        else:
            #load results from cache
            all_results = json.loads(all_results)
        
        #total number of results
        total = len(all_results)
        #subset of results for appropriate page
        results_subset = all_results[offset: offset + per_page]
        #create pagination using Flask Paginate library, 
        pagination = Pagination(page=page, per_page=per_page, total=total, record_name='results', css_framework='foundation')
       
        #get sets of values for each sidebar query parameter from results
        unique_repositories = set(result.get('json_repository') for result in all_results)
        unique_languages = set(result.get('json_language') for result in all_results)
        unique_materials = set(result.get('json_material') for result in all_results)

        #remove question marks so 'Paper?' is treated same as 'Paper' in sidebar links, for example
        unique_repositories = set(repository.replace('?', '') for repository in unique_repositories)
        unique_languages = set(language.replace('?', '') for language in unique_languages)
        unique_materials = set(material.replace('?', '') for material in unique_materials)

        #query params dictionary created for current search of all, can be augmented for sidebar links below
        query_params = {'query': '*'}

        #use function to get sidebar links for results page
        #these will redirect to another results page composed of any existing queries and new query including sidebar value choice
        repository_links = sidebar_counts(results=all_results, item_names=unique_repositories, query_params=query_params, 
            json_key='json_repository', item_key='repository')
        language_links = sidebar_counts(results=all_results, item_names=unique_languages, query_params=query_params,
            json_key='json_language', item_key='language')
        material_links = sidebar_counts(results=all_results, item_names=unique_materials, query_params=query_params,
            json_key='json_material', item_key='material')

        #returns rendered template with index subset for page, query string parameters, pagination, 
        #sidebar link data and total count of results 
        return render_template('index.html', results=results_subset, query=query, pagination=pagination, 
            language_links=language_links, repository_links=repository_links, material_links=material_links, count=total)


@app.route('/viewer.html', methods=['GET'])
def viewer():
    """
    Gets manifest url from query string and sanitises,
    then uses it to render a Mirador IIIF viewer.

    Returns:
    - Rendered template containing a Mirador IIIF viewer for manifest.
    - Done for each displayed link in results/index.
    """
    
    manifest_url = request.args.get('manifest')
    #use function to sanitise url with nh3 library
    manifest_url = extract_html_text(manifest_url)
    #return viewer template for IIIF url
    return render_template('viewer.html', manifest_url=manifest_url)

#starts the flask application
if __name__ == '__main__':
    app.run(debug=True)
