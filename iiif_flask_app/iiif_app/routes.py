import os
import json
import re
from natsort import natsorted
from flask import Flask, render_template, request, redirect, url_for
from flask import  current_app as app
from flask_paginate import Pagination
from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.query import And, Term, Every
from whoosh.sorting import FieldFacet
from whoosh.collectors import FacetCollector
from whoosh import collectors
from whoosh import sorting
from config import Config
from iiif_app.forms import SearchForm
from iiif_app.utils import custom_get, custom_get_int, extract_html_text, sidebar_counts, make_cache_key_excluding_page

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

#access the Whoosh index and cache from the app configuration
ix = app.config['SEARCH_INDEX']
cache = app.config['CACHE']

#the following section contains the app routes for the creation of the website
#and rendering html templates
#templates stored in 'templates' folder alongside the file for this script
#cache used for routes or items that do not change due to user input

@app.context_processor
def main():
    """
    Allows form variables invoked by SearchForm to be accessible across app
    SearchForm method allows us to utilise csrf protection on user searches
    
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

@app.route('/invalid-query')
def invalid_query():
    """Render invalid query html template."""
    return render_template('invalid_query.html')

@app.route('/invalid-manifest')
def invalid_manifest():
    """Render invalid manifest html template."""
    return render_template('invalid_manifest.html')

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
        #check if query is not blank and is string
        query = form.searched.data.strip()
        if query is not None and isinstance(query, str):
            #clean up query
            query = re.sub(r'\W+\s*', ' ', query).strip()
            #return query to results route with url parameters extracted above
            return redirect(url_for('results', query=query, repository=repository, language=language, material=material, author=author))
            
    #if form not valid return invalid query route
    return redirect(url_for('invalid_query'))

@app.route('/results')
def results():
    """
    Handles search result display, including filters and pagination.

    Retrieves search query and filters from the URL, executes a Whoosh search, applies
    sidebar filters, caches sidebar results, and paginates the response.

    Returns:
        Results html template with:
        - Search results for current page.
        - Active query/filter parameters.
        - Pagination controls.
        - Sidebar filter link data.
        - Total result count.
    """

    #extract main query and sidebar filters from URL query string
    user_query = custom_get(param='query')
    repository = custom_get(param='repository')
    language = custom_get(param='language')
    material = custom_get(param='material')
    author = custom_get(param='author')

    #put queries in dictionary for use below in sidebar function
    query_params = {'query': user_query, 'repository': repository, 'language': language, 'material': material, 'author': author}

    #get current page number, calculate result offset
    page = custom_get_int('page')
    per_page = 20
    offset = (page - 1) * per_page

    #use Whoosh search index to initialize search
    with ix.searcher() as searcher:  
        #create Whoosh parser for searchable fields using index
        parser = MultifieldParser(['iiif_path', 'json_label', 'json_date', 'json_description', 'json_thumbnail', 'json_author'], ix.schema)     
        
        #use Every() to match all documents if no user query is provided
        if not user_query or user_query.strip() == "*":
            search_query = Every()
        #otherwise, parse the user query and append a wildcard (*) to allow partial matches
        else:
            search_query = parser.parse(f"{user_query}*")

        #filters added to this list from query string items
        filters = []
        #for each sidebar filter check if a value is present in the query string
        #if present, create a QueryParser for the corresponding indexed field
        #append the parsed queries to the filters list.
        if repository:
            filters.append(QueryParser('json_repository', schema=ix.schema).parse(repository))
        if language:
            filters.append(QueryParser('json_language', schema=ix.schema).parse(language))
        if material:
            filters.append(QueryParser('json_material', schema=ix.schema).parse(material))
        if author:
            filters.append(QueryParser('json_author', schema=ix.schema).parse(author))         

        #create combined query from filters and user query
        query = And([search_query] + filters)
        
        #run the search with sorting and pagination
        results = searcher.search(query, limit=offset + per_page, sortedby="iiif_path")
        results_subset = results[offset: offset + per_page]

        #generate cache key for query excluding page number
        cache_key = make_cache_key_excluding_page()
        cached_data = cache.get(cache_key)

        #if query cached, load result count and sidebar links from cache
        if cached_data:
            total = cached_data['total_count']
            repository_links = cached_data['sidebar']['repository']
            language_links = cached_data['sidebar']['language']
            material_links = cached_data['sidebar']['material']
            author_links = cached_data['sidebar']['author']
        #otherwise generate query count and sidebar links
        else:
            #count total matching results
            total = searcher.search(query, limit=None).scored_length()

            #generate sidebar filter links with counts
            repository_links = sidebar_counts(query=query, query_params=query_params, searcher=searcher,
                json_key='json_repository', item_key='repository')
            language_links = sidebar_counts(query=query,  query_params=query_params, searcher=searcher,
                json_key='json_language', item_key='language')
            material_links = sidebar_counts(query=query, query_params=query_params, searcher=searcher,
                json_key='json_material', item_key='material')
            author_links = sidebar_counts(query=query, query_params=query_params, searcher=searcher,
                json_key='json_author', item_key='author')

            #cache sidebar link data and total count for future requests
            cache.set(cache_key, {
                'total_count': total,
                'sidebar': {
                    'repository': repository_links,
                    'language': language_links,
                    'material': material_links,
                    'author': author_links
                }
            }, timeout=300)

        #create pagination controls using Flask Paginate library 
        pagination = Pagination(page=page, per_page=per_page, total=total, record_name='results', css_framework='foundation')

        #render search results template with supporting data
        return render_template('results.html', results=results_subset, query_params=query_params, pagination=pagination, language_links=language_links, 
            repository_links=repository_links, material_links=material_links, author_links=author_links, count=total)


@app.route('/index')
def list_files():
    """
    Handles index display, including filters and pagination.

    Executes a query to list all entries in the Whoosh index.
    Sidebar filter counts are generated and cached to improve performance.

    Returns:
        Index html template with:
        - Index results for current page
        - Query parameters (set to wildcard).
        - Pagination controls.
        - Sidebar filter link data.
        - Total result count.
    """
    
    #get current page number, calculate result offset
    page = custom_get_int('page')
    per_page = 20
    offset = (page - 1) * per_page

    #use Whoosh search index to generate all files
    with ix.searcher() as searcher:

        #as we are locating all files, Whoosh Every used for query
        query = Every('iiif_path')
        #wildcard used for queries dictionary for sidebar function
        query_params = {'query': '*'}

        #run the search with sorting and pagination
        results = searcher.search(query, limit=offset + per_page, sortedby="iiif_path")
        results_subset = results[offset: offset + per_page]
        
        #generate cache key for query excluding page number
        cache_key = make_cache_key_excluding_page()
        cached_data = cache.get(cache_key)

        #if query cached, load index count and sidebar links from cache
        if cached_data:
            total = cached_data['total_count']
            repository_links = cached_data['sidebar']['repository']
            language_links = cached_data['sidebar']['language']
            material_links = cached_data['sidebar']['material']
            author_links = cached_data['sidebar']['author']
        #otherwise generate query count and sidebar links
        else:
            #count total matching results
            total = searcher.search(query, limit=None).scored_length()

            #generate sidebar filter links with counts
            repository_links = sidebar_counts(query=query, query_params=query_params, searcher=searcher,
                json_key='json_repository', item_key='repository')
            language_links = sidebar_counts(query=query,  query_params=query_params, searcher=searcher,
                json_key='json_language', item_key='language')
            material_links = sidebar_counts(query=query, query_params=query_params, searcher=searcher,
                json_key='json_material', item_key='material')
            author_links = sidebar_counts(query=query, query_params=query_params, searcher=searcher,
                json_key='json_author', item_key='author')

            #cache sidebar link data and total count for future requests
            cache.set(cache_key, {
                'total_count': total,
                'sidebar': {
                    'repository': repository_links,
                    'language': language_links,
                    'material': material_links,
                    'author': author_links
                }
            }, timeout=300)

        #create pagination controls using Flask Paginate library 
        pagination = Pagination(page=page, per_page=per_page, total=total, record_name='results', css_framework='foundation')

        #render index template with supporting data
        return render_template('index.html', results=results_subset, query_params=query_params, pagination=pagination, language_links=language_links, 
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
        #if manifest url not valid return invalid manifest route
        return redirect(url_for('invalid_manifest'))

    #return viewer template for IIIF url
    return render_template('viewer.html', manifest_url=manifest_url)
