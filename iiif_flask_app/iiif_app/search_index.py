import os
import json
import re
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT
from whoosh.analysis import StandardAnalyzer, CharsetFilter
from whoosh.writing import AsyncWriter
from whoosh.support.charset import accent_map
from config import Config
from iiif_app.utils import safe_json_get, extract_html_text, json_value_extract_clean, get_metadata_value


#ensure file is run from correct directory in editor
os.chdir(os.path.dirname(__file__))

def initialize_import_index(index_dir='index', files_directory='iiif_app/files'):
    """
    Initializes the Whoosh index, processes JSON files, and populates the index with documents.

    Parameters:
    - index_dir: Directory where the Whoosh index is created or opened.
    - files_directory: Directory containing the JSON files to be indexed.

    Returns:
    - ix: The Whoosh index object.
    """

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

    #create or open the index file using the schema created above
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    ix = create_in(index_dir, schema)

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
        repositories = Config.REPOSITORIES
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
    ix = open_dir(index_dir)
    return ix

