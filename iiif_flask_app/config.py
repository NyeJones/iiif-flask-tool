import os

class Config:
    #access secret key for app security
    SECRET_KEY = os.environ.get('IIIF_FLASK_KEY')
    #home page background image
    #use image api from sequences in manifest, followed by "/467,857,2418,1397/full/0/default.jpg" for correct sizing
    BACKGROUND_IMAGE = "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8415234c/f14/467,857,2418,1397/full/0/default.jpg"
    #home page introduction image
    #use image api from sequences in manifest, followed by "/55,111,2844,3035/full/0/default.jpg" for correct sizing
    INTRO_IMAGE = "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8415234c/f17/55,111,2844,3035/full/0/default.jpg"
    #home page main title takes list of strings
    MAIN_TITLE = ["Main title here"]
    #caption text takes list of strings
    CAPTION_TEXT = ["Caption text for home page introduction image"]
    #home page long introduction takes a list of strings
    LONG_INTRO = ["Introduction text here."]
    #repositories takes a dictionary, for identifying iiif repository from iiif uri
    #use part of uri that is always there for relevant repository
    #see example below - key is "cudl" which is always in the iiif uris for Cambridge University Library
    #add entries for every repository included in your site
    REPOSITORIES = {'cudl': 'Cambridge University Library'}
    #about page text takes a list of strings
    ABOUT = ["About page text"]
    #project team text takes a list of strings
    PROJECT_TEAM = ["Person 1, email@cam.ac.uk", 'Person_2, email@gmail.com']
    #advisory board text takes a list of strings
    ADVISORY_BOARD = [
        "Person 1 - Affiliations etc",
        "Person 2 - Affiliations etc",
        "Person 3 - Affiliations etc",
        ]
    #footer takes a dictionary, key is display text, value is hyperlink - links for site footer section
    #follow the format below and add relevant links
    FOOTER = { 
        "International Image Interoperability Framework (IIIF)": "https://iiif.io/"
        }
    #base urls takes a list of strings, these are used for security purposes to say which sites are ok to link to
    #if you're including an iiif api you'll need to add the provider to the list if not already there
    #as in this format: "lib.cam.ac.uk", "*.lib.cam.ac.uk" - 2 entries for each provider
    BASE_URLS = [
        "lib.cam.ac.uk",
        "*.lib.cam.ac.uk",
        "gallica.bnf.fr/",
        "*.gallica.bnf.fr/",
        "bodleian.ox.ac.uk",
        "*.bodleian.ox.ac.uk",
        "princeton.edu",
        "*.princeton.edu",
        "digitalcommonwealth.org",
        "*.digitalcommonwealth.org",
        "e-codices.ch",
        "*.e-codices.ch",
        "e-codices.unifr.ch",
        "*.e-codices.unifr.ch",
        "lib.harvard.edu",
        "*.lib.harvard.edu",
        "ugent.be",
        "*.ugent.be",
        "digitale-sammlungen.de",
        "*.digitale-sammlungen.de",
        "irht.cnrs.fr",
        "*.irht.cnrs.fr",
        "contentdm.oclc.org",
        "*.contentdm.oclc.org",
        "st-andrews.ac.uk",
        "*.st-andrews.ac.uk",
        "lib.ncsu.edu",
        "*.lib.ncsu.edu",
        "digi.vatlib.it",
        "*.digi.vatlib.it",
        "library.villanova.edu",
        "*.library.villanova.edu",
        "folger.edu",
        "*.folger.edu",
        "lancaster.ac.uk",
        "*.lancaster.ac.uk",
        "universiteitleiden.nl",
        "*.universiteitleiden.nl",
        "fragmentarium.ms",
        "*.fragmentarium.ms",
        "si.edu",
        "*.si.edu",
        "archivelab.org",
        "*.archivelab.org",
        "europeana.eu",
        "*.europeana.eu",
        "library.ucla.edu",
        "*.library.ucla.edu",
        "library.utoronto.ca",
        "*.library.utoronto.ca",
        "unige.ch",
        "*.unige.ch",
        "wellcomecollection.org",
        "*.wellcomecollection.org",
        "uni-goettingen.de",
        "*.uni-goettingen.de",
        "getty.edu",
        "*.getty.edu",
        "library.uu.nl",
        "*.library.uu.nl",
        "dri.ie",
        "*.dri.ie",
        "library.brown.edu",
        "*.library.brown.edu",
        "nls.uk",
        "*.nls.uk",
        "davidrumsey.com",
        "*.davidrumsey.com",
        "e-manuscripta.ch",
        "*.e-manuscripta.ch",
        "e-rara.ch",
        "*.e-rara.ch",
        "loc.gov",
        "*.loc.gov",
        "qdl.qa",
        "*.qdl.qa",
        "dimu.org",
        "*.dimu.org",
        "manchester.ac.uk",
        "*.manchester.ac.uk"
    ]