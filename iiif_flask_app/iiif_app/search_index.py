import os
import json
import re
import logging
import time
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT
from whoosh.analysis import StandardAnalyzer, CharsetFilter
from whoosh.writing import AsyncWriter
from whoosh.support.charset import accent_map
from config import Config
from iiif_app.utils import safe_json_get, extract_html_text, json_value_extract_clean, get_metadata_value

#ensure file is run from correct directory in editor
os.chdir(os.path.dirname(__file__))

#configure logger for this module
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

#path to the file that stores the timestamp of the last successful index update
INDEX_TIMESTAMP_PATH = 'index/.last_indexed'

def needs_reindex(files_directory):
    """
    Determines whether the search index needs to be updated based on file modification times.

    This function checks if any `.json` files in the given directory (and its subdirectories)
    have been modified more recently than the last recorded index update time. Also checks
    directory level modification times.

    Returns:
        True if:
            - The index timestamp file does not exist, or
            - Any directory has been modified after the last index time.
            - Any `.json` file has been modified after the last index time.
        False otherwise and index can be loaded from existing files.
    """    
    if not os.path.exists(INDEX_TIMESTAMP_PATH):
        return True

    last_index_time = float(open(INDEX_TIMESTAMP_PATH).read().strip())

    for root, _, files in os.walk(files_directory):
        #check for directory-level changes
        if os.path.getmtime(root) > last_index_time:
            return True
        #check for file-level changes
        for file in files:
            if not file.endswith('.json'):
                continue
            path = os.path.join(root, file)
            if os.path.getmtime(path) > last_index_time:
                return True 
    return False

def update_index_timestamp():
    """
    Updates the index timestamp file with the current time.

    This function writes the current UNIX timestamp to a predefined file
    (`INDEX_TIMESTAMP_PATH`). It is used to record the last time the search
    index was updated, allowing future checks to determine if reindexing is needed.
    """
    with open(INDEX_TIMESTAMP_PATH, 'w') as f:
        f.write(str(time.time()))

def initialize_import_index(index_dir='index', files_directory='iiif_app/files'):
    """
    Checks if reindexing is necessary by checking file modification times.
    If reindexing is not needed, loads the existing index and sidebar filter data.
    If reindexing is needed creates new Whoosh index, processes JSON files, 
    and populates the index with documents.

    Parameters:
    - index_dir: Directory where the Whoosh index is created or opened.
    - files_directory: Directory containing the iiif JSON files to be indexed.

    Returns:
    - ix: The Whoosh index object.
    - index_lists: A dictionary of sets for creating sidebar filters in the app.
    """

    #initialise analyzer for Whoosh search engine, essentially a tokenizer with filters.
    #no stop words and conversion of accented characters to standardised in our case.
    no_stop_analyzer = StandardAnalyzer(stoplist=None) | CharsetFilter(accent_map)

    #define the schema for the search index
    #treat fields as text, store in the index, add analyser initialised above, make sortable
    schema = Schema(
        iiif_path=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_label=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_date=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_language=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_material=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_description=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_repository=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_thumbnail=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        json_author=TEXT(stored=True, analyzer=no_stop_analyzer, sortable=True),
        )

    #create index directory if not present
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)

    #create path for index sidebar list storage
    index_lists_path = os.path.join(index_dir, 'index_lists.json')
    
    #check if index and index lists for sidebar need to be updated or created
    #if not required load them
    if not needs_reindex(files_directory):
        #load index from file
        ix = open_dir(index_dir)
        #load index lists dictionary from json file
        with open(index_lists_path, 'r', encoding='utf-8') as f:
            index_lists = {k: set(v) for k, v in json.load(f).items()}
        #return index and index lists for sidebar
        return ix, index_lists
    #otherwise index and index lists are not present, create them
    else:
        ix = create_in(index_dir, schema)

        #create index sets for use in sidebar
        index_lists = {'repository': set(), 'language': set(), 'material': set(), 'author': set()}

        #initialize writer to write data to index
        #use asyncwriter imported above to avoid concurrency locks on writing to index
        writer = AsyncWriter(ix)

        #set initialized to check for duplicate iiif records and empty id fields
        seen_ids = set()

        #number of files to process before committing to index
        batch_size = 100
        #initialize counter for tracking processed files
        counter = 0

        #loop through files directory and extract file path of each iiif manifest
        for root, dirs, files in os.walk(files_directory):
            for file in files:
                if file.endswith('json'):
                    file_path = os.path.join(root, file)
                    try:
                        #check if json data can be loaded from file path
                        with open(file_path, 'r', encoding='utf-8') as json_file:
                            json_record = json.load(json_file)
                            #get iiif id from record
                            json_id_val = safe_json_get(json_record, '@id') or safe_json_get(json_record, 'id')

                            #if json id not found, log accordingly and continue to next file
                            if not json_id_val:
                                logger.warning(f"Missing record ID, skipping file: {file_path}")
                                continue

                            #use function to sanitise data with nh3 library and extract as string
                            json_id = extract_html_text(json_id_val)[0]

                            #if json_id in seen ids log accordingly and continue to next file
                            if json_id in seen_ids:
                                logger.warning(f"Duplicate file, skipping file: {file_path}")
                                continue

                            #if json_id ok add to seen ids and move on to data extraction
                            seen_ids.add(json_id)

                            #use functions to extract and prepare relevant data using key
                            #sanitise and clean data for key value, return 'N/A' if None
                            #extract all matching values as list
                            #convert list into string for each key, joined with '|' where more than one value
                            #finish with a list of values and a joined list of values for each category
                            #these are used for sidebar and whoosh index respectively

                            json_label_val = safe_json_get(json_record, 'label')
                            json_label_ls = json_value_extract_clean(json_label_val)
                            json_label = ' | '.join(json_label_ls)
                            
                            json_description_val = safe_json_get(json_record, 'description')
                            json_description_ls = json_value_extract_clean(json_description_val)
                            json_description = ' | '.join(json_description_ls)

                            #create default value of ['N/A'] for additional metadata categories
                            json_date_ls = ['N/A']
                            json_language_ls = ['N/A']
                            json_material_ls = ['N/A']
                            json_author_ls = ['N/A']

                            #use function to extract iiif metadata if there
                            metadata = safe_json_get(json_record, 'metadata')
                            
                            if metadata:

                                #if metadata present we need to use a function to extract any subcategories
                                #these are based on broad, yet reliable, regex substrings, such as 'date', 'language', 'material'
                                #this is because metadata categories are decided on by institutions and
                                #not standardised as part of the iiif schema
                                #we also use our json_value_extract_clean to sanitise, fully extract and clean json values

                                #extract all matching values as list
                                #convert list into string for each category, joined with '|' where more than one value
                                #finish with a list of values and a joined list of values for each category
                                #these are used for sidebar and whoosh index respectively

                                json_date_ls = get_metadata_value(metadata, r'date')
                                json_date_ls = json_value_extract_clean(json_date_ls)
                                json_date = ' | '.join(json_date_ls)

                                json_language_ls = get_metadata_value(metadata, r'^(text language|language)\S*$')
                                json_language_ls = json_value_extract_clean(json_language_ls)
                                index_lists['language'].update(json_language_ls)
                                json_language = ' | '.join(json_language_ls)

                                json_material_ls = get_metadata_value(metadata, r'material')
                                json_material_ls = json_value_extract_clean(json_material_ls)
                                index_lists['material'].update(json_material_ls)
                                json_material = ' | '.join(json_material_ls)

                                json_author_ls = get_metadata_value(metadata, r'^(author|creator)\S*$')
                                json_author_ls = json_value_extract_clean(json_author_ls)
                                index_lists['author'].update(json_author_ls)
                                json_author = ' | '.join(json_author_ls)

                            #create default value of 'N/A' for repository
                            json_repository = 'N/A'

                            #repository for each item identified by substring within manifest id
                            #loop through repositories imported from config
                            repositories = Config.REPOSITORIES
                            for key, value in repositories.items():
                                #if repository key found in id then give it repository value
                                if re.search(key, json_id):
                                    json_repository = value
                                    index_lists['repository'].add(json_repository)
                                    break

                            #use Beautiful Soup function to extract thumbnail image id
                            #images are well nested so need a few uses of function, return None if no image id
                            first_sequence = safe_json_get(json_record, 'sequences', index=0, logging=False)
                            first_canvas = safe_json_get(first_sequence, 'canvases', index=0, logging=False)
                            first_image = safe_json_get(first_canvas, 'images', index=0, logging=False)
                            resource = safe_json_get(first_image, 'resource', logging=False)
                            service = safe_json_get(resource, 'service', logging=False)
                            if service:
                                iiif_image_url = safe_json_get(service, '@id', logging=False) or safe_json_get(service, 'id', logging=False)
                            else:
                                iiif_image_url = safe_json_get(resource, '@id', logging=False) or safe_json_get(resource, 'id', logging=False)
                            
                            #if image url not found log accordingly and make json_thumbnail None
                            if not iiif_image_url:
                                logger.warning(f"No image URL found for record ID: {json_id}")
                                json_thumbnail = None
                            else:
                                #perform data sanitisation on url and extract as string
                                iiif_image_url = extract_html_text(iiif_image_url)[0]
                                #suffix patterns to remove from image id if there
                                suffix_remove_patterns = [r'/full/.*/0/.*jpg']
                                #new suffix to add to the end of all thumbnail urls, to get correct size for thumbnail
                                new_suffix = '/full/!200,200/0/default.jpg'

                                #initialize json_thumbnail with the default URL
                                json_thumbnail = iiif_image_url + new_suffix

                                #loop through patterns and remove if there
                                for pattern in suffix_remove_patterns:
                                    #if pattern present replace with new suffix in image url
                                    if re.search(pattern, iiif_image_url):
                                        json_thumbnail = re.sub(pattern, new_suffix, iiif_image_url)
                                        break

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
                                json_author=json_author
                                )

                            #increment counter for each file processed
                            counter += 1
                            
                            #commit after every 'batch_size' files
                            if counter % batch_size == 0:
                                #commit the current batch of documents to the index
                                writer.commit()
                                #reinitialize the writer for the next batch
                                writer = AsyncWriter(ix)

                    #if there is an error print filename and error to console
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding JSON in file {file_path}: {e.msg}")

        #commit data for all manifests to the Whoosh index
        writer.commit()
        #convert sets to lists for JSON serialization
        serializable_index_lists = {k: list(v) for k, v in index_lists.items()}

        #save index lists for re-use
        with open(index_lists_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_index_lists, f, indent=2, ensure_ascii=False)


        #open the Whoosh search index for searching with all manifest data included
        ix = open_dir(index_dir)
        #index has been updated, due to changes in files, record change in file
        update_index_timestamp()
        return ix, index_lists