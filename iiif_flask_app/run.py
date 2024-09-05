from iiif_app import create_app
import os

#ensure file is run from correct directory in editor
os.chdir(os.path.dirname(__file__))

#create app and run
app = create_app()
if __name__ == '__main__':
    app.run(debug=True)