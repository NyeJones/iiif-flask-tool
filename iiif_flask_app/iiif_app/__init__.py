import os
from flask import Flask
from flask_caching import Cache
from flask_talisman import Talisman
from iiif_app.search_index import initialize_import_index
from config import Config

#ensure file is run from correct directory in editor
os.chdir(os.path.dirname(__file__))

def create_app():
	"""
	Create and configure a Flask application instance.

	This function initializes and configures a Flask app with caching, search indexing,
	security settings, and routes. More details below.

	Returns:
		A configured Flask application instance.
	"""

	#create a Flask app 
	app = Flask(__name__)

	#initialize flask-cache to increase app efficiency, add to app
	cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
	app.config['CACHE'] = cache

	#ensure the app context is available when initializing the search index
	with app.app_context():
		#check if the index and sidebar lists are already cached
		index_lists = cache.get('index_lists')
		ix = cache.get('search_index')
		#if not present in cache add to cache
		if not ix or not index_lists:
			#initialize the app index, index lists for sidebar and index data using imported function
			index_directory = 'index'
			files_directory = 'iiif_app/files'
			ix, index_lists = initialize_import_index(index_dir=index_directory, files_directory=files_directory)

			#cache the result to avoid re-indexing in subsequent requests
			cache.set('search_index', ix, timeout=86400)
			cache.set('index_lists', index_lists, timeout=86400)

	#add index to app
	app.config['SEARCH_INDEX'] = ix
	#add index lists for sidebar operations to app
	app.config['INDEX_LISTS'] = index_lists

	#create route to static folder for css and javascript files
	app.static_folder = 'static'
	#import config data from config file, including security key, into app
	app.config.from_object(Config)
	#set SESSION_COOKIE_SAMESITE to 'Lax'
	SESSION_COOKIE_SAMESITE = 'Lax'
	#prevents JavaScript from accessing the session cookie, XSS attack protection
	SESSION_COOKIE_HTTPONLY = True
	#ensures that cookies are only transmitted over HTTPS connections
	#change to True for production if using https, so cookies are sent over secure channels
	SESSION_COOKIE_SECURE = False  # Since HTTPS might not be used in development

	#list of base urls for validation in Mirador viewer and thumbnails
	#more base urls can be added to the list in the config file, following pattern there
	base_urls = app.config ['BASE_URLS']

	#Content Security Policy (CSP) directives - rules that define the allowed sources for various types of content
	#style needs to be 'unsafe-inline' for mirador generated inline style elements to work
	csp = {
	    'default-src': ['\'self\'', 'https://maxcdn.bootstrapcdn.com', 'https://ajax.googleapis.com'],
	    'connect-src': ['\'self\''],
	    'img-src': ['\'self\''],
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

	#import and register app routes after app and ix are set up
	with app.app_context():
		import iiif_app.routes

	return app





