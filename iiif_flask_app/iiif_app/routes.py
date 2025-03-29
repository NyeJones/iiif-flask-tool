import os
import json
import re
from natsort import natsorted
from flask import Flask, render_template, request, redirect, url_for
from flask import  current_app as app
from flask_paginate import Pagination
from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.query import And
from whoosh import sorting
from config import Config
from iiif_app.forms import SearchForm
from iiif_app.utils import custom_get, custom_get_int, extract_html_text, sidebar_counts


#get config data for site from file
#iiif image uris
background_image = Config.BACKGROUND_IMAGE
intro_image = Config.INTRO_IMAGE

#various text items to fill parts of the site
main_title = Config.MAIN_TITLE
caption_text = Config.CAPTION_TEXT
caption_link = Config.CAPTION_LINK
long_intro = Config.LONG_INTRO
about_data = Config.ABOUT
proj_team_data = Config.PROJECT_TEAM
ad_board_data = Config.ADVISORY_BOARD
privacy_data = Config.PRIVACY

#dictionary of footer names and urls
footer_data = Config.FOOTER
#dictionary of repositories and identifiers
repositories = Config.REPOSITORIES

#access the Whoosh index, index lists for sidebar and cache from the app configuration
ix = app.config['SEARCH_INDEX']
index_lists = app.config['INDEX_LISTS']
cache = app.config['CACHE']

#the following section contains the app routes for the creation of the website
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
    return render_template('home.html', main_title=main_title, caption_text=caption_text, caption_link=caption_link,
        long_intro=long_intro, background_image=background_image, intro_image=intro_image)

@app.route('/about')
@cache.cached(timeout=86400)
def about():
    """Render about page html template."""
    return render_template('about.html', about_data=about_data)

@app.route('/privacy')
@cache.cached(timeout=86400)
def privacy():
    """Render privacy page html template."""
    return render_template('privacy.html', privacy_data=privacy_data)

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
    author = custom_get(param='author')

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
            return redirect(url_for('results', query=query, repository=repository, language=language, material=material, author=author))

    
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
    author = custom_get(param='author')

    #put queries in dictionary for use below in sidebar function
    query_params = {'query': user_query, 'repository': repository, 'language': language, 'material': material, 'author': author}

    #use Whoosh search index for search using query parameters
    with ix.searcher() as searcher:
        
        #use function to safely extract page number from query string
        page = custom_get_int('page')
        #create additional page variables
        per_page = 20
        offset = (page - 1) * per_page
        
        #creates Whoosh parser for appropriate fields using search index
        parser = MultifieldParser(['iiif_path', 'json_label', 'json_date', 'json_description', 'json_thumbnail', 'json_author'], ix.schema)
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
        author_parser = QueryParser('json_author', schema=ix.schema)
        author_query = author_parser.parse(author)
        filters.append(author_query)         

        #create combined query from filters and user query then search Whoosh index
        search_query = And([search_query] + filters)
        #extract the results and sort them by iiif path using natsorted for numerical sorting
        results = searcher.search(search_query, limit=None)
        results = natsorted(results, key=lambda x: x['iiif_path'])
        #convert results to list of dictionaries
        results = [dict(result) for result in results]

        #total number of results
        total = len(results)
        #subset of results for appropriate page
        results_subset = results[offset: offset + per_page]
        #create pagination using Flask Paginate library, 
        pagination = Pagination(page=page, per_page=per_page, total=total, record_name='results', css_framework='foundation')

        #use function to get sidebar links for results page
        #these will redirect to another results page composed of any existing queries and new query including sidebar value choice
        repository_links = sidebar_counts(results=results, index_lists=index_lists, query_params=query_params, 
            json_key='json_repository', item_key='repository')
        language_links = sidebar_counts(results=results, index_lists=index_lists, query_params=query_params,
            json_key='json_language', item_key='language')
        material_links = sidebar_counts(results=results, index_lists=index_lists, query_params=query_params,
            json_key='json_material', item_key='material')
        author_links = sidebar_counts(results=results, index_lists=index_lists, query_params=query_params,
            json_key='json_author', item_key='author')

        #returns rendered template with results subset for page, query string parameters, pagination, 
        #sidebar link data and total count of results 
        return render_template("results.html", results=results_subset, query_params=query_params, pagination=pagination,
            repository_links=repository_links, language_links=language_links, material_links=material_links, author_links=author_links, count=total)


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
            'json_description', 'json_repository', 'json_thumbnail', 'json_author'], ix.schema)
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
        #if nothing cached assemble index
        if all_results is None:
            #perform search of index to generate all results using parser generated above
            all_results = searcher.search(query, limit=None)
            #sort results by iiif path using natsorted for numerical sorting
            all_results = natsorted(all_results, key=lambda x: x['iiif_path'])
            #convert results to list of dictionaries for caching
            all_results = [dict(result) for result in all_results]
            #cache the results for future use
            cache.set(cache_key_all_results, json.dumps(all_results), timeout=86400)
        else:
            # Load results from cache if they are there
            all_results = json.loads(all_results)
        
        #total number of results
        total = len(all_results)
        #subset of results for appropriate page
        results_subset = all_results[offset: offset + per_page]
        #create pagination using Flask Paginate library
        pagination = Pagination(page=page, per_page=per_page, total=total, record_name='results', css_framework='foundation')

        #query params dictionary created for current search of all, can be augmented for sidebar links below
        query_params = {'query': '*'}

        #use function to get sidebar links for results page
        #these will redirect to another results page composed of any existing queries and new query including sidebar value choice
        repository_links = sidebar_counts(results=all_results, index_lists=index_lists, query_params=query_params, 
            json_key='json_repository', item_key='repository')
        language_links = sidebar_counts(results=all_results, index_lists=index_lists, query_params=query_params,
            json_key='json_language', item_key='language')
        material_links = sidebar_counts(results=all_results, index_lists=index_lists, query_params=query_params,
            json_key='json_material', item_key='material')
        author_links = sidebar_counts(results=all_results, index_lists=index_lists, query_params=query_params,
            json_key='json_author', item_key='author')

        #returns rendered template with index subset for page, query string parameters, pagination, 
        #sidebar link data and total count of results 
        return render_template('index.html', results=results_subset, query=query, pagination=pagination, language_links=language_links, 
            repository_links=repository_links, material_links=material_links, author_links=author_links, count=total)

@app.route('/viewer.html', methods=['GET'])
def viewer():
    """
    Gets manifest url from query string and sanitises,
    then uses it to render a Mirador IIIF viewer.

    Returns:
    - Rendered template containing a Mirador IIIF viewer for manifest.
    - Done for each displayed link in results/index.
    - If the manifest URL is invalid or missing, renders an error template with a message.
    """
    
    manifest_url = request.args.get('manifest')
    #use function to sanitise url with nh3 library
    manifest_url = extract_html_text(manifest_url)

    if not manifest_url:
        #return invalid query template if invalid or blank
        invalid_msg = 'An error occurred while processing the manifest URL for viewer.'
        return render_template('invalid-query.html', invalid_msg=invalid_msg)

    #return viewer template for IIIF url
    return render_template('viewer.html', manifest_url=manifest_url)
