import requests
import json
import os
import re


def iiif_validation(input_uris):
    '''Validates a list of input IIIF manifest uris.
    Uses Requests library to get data from uri list as json items.
	If not a valid IIIF uri, not valid JSON or unable to fetch data
	gives error message for that uri. 
	Returns a list of json data items for each valid uri.
	'''
    validated_data = []
    for uri in input_uris:
        print(f'Processing {uri}')
        if not uri.strip():  # Check if the uri is empty or blank
            print("Empty uri, skipping...")
            continue
        try:
            response = requests.get(uri)
            response.raise_for_status()  # Raise an error for non-200 status codes
            data = response.json()  # Directly parse JSON response
            data_tuple = (uri, data)
            validated_data.append(data_tuple)
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f'Error processing uri "{uri}": {e}')
        except Exception as e:
            print(f'An unexpected error occurred: {e}')
    return validated_data

def iiif_process_save(input_iiif_ls):
	'''Inputs a list of IIIF json files: manifests and collections.
    If item is a IIIF collection, it extracts the manifest uris from it,
    validates each manifest uri, and saves the validated manifests as json.
    If an item is a IIIF manifest, it directly saves the manifest as json.
    If an item is neither a IIIF manifest nor a IIIF collection, it prints
    a message indicating that the item is not included in the data.
    Also handles KeyError exceptions, which occur if a required key is missing
    in the IIIF data item, together with other exceptions.
	'''
	for uri, item in input_iiif_ls:
	    try:
	        item_type = item.get('@type')
	        if item_type == 'sc:Collection':
	            collection_uris = []
	            for dic in item.get('manifests', []):
	                coll_id = dic.get('@id')
	                if coll_id:
	                    collection_uris.append(coll_id)
	            validated_coll_data = iiif_validation(collection_uris)
	            iiif_process_save(validated_coll_data)
	        elif item_type == 'sc:Manifest':
	            save_manifest(item)
	        else:
	            print(f'No "@type" found for item: {uri}. Not included in data')
	    except KeyError as e:
	        print(f'Error processing item {uri}: Key {e} is missing. Skipping...')
	    except Exception as e:
	        print(f'An error occurred processing item {uri}: {e}. Skipping...')

def save_manifest(manifest):
	'''Inputs a single IIIF manifest.
	Extracts identifier from uri in manifest using regex.
	Uses identifier as part of file path for manifest.
	Saves manifest to outputs directory as json.'''
	uri = manifest['@id']
	identifier = re.search(r'https://(.+)', uri).group(1)
	underscore_id = identifier.replace('/', '_')
	if re.search(r'\.json$', underscore_id):
		file_path = f'outputs/{underscore_id}'
	else:
		file_path = f'outputs/{underscore_id}.json'
	with open(file_path, 'w', encoding='utf-8') as json_file:
		json.dump(manifest, json_file, indent=4)

#ensure file is run from correct directory in editor
os.chdir(os.path.dirname(__file__))

#set up list for input uris
input_uris = []

#open input file in read format and add each line from file as item
#items in file should be on separate lines
with open('input/input.txt', 'r') as input_file:
	for line in input_file:
		line = line.strip()
		input_uris.append(line)


#validate input uris and get json data for uris using function
validated_data = iiif_validation(input_uris)

#process validated iiif data and save as directory of manifests
iiif_process_save(validated_data)

