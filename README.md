# iiif-flask-app

This tool aims to solve a general problem in the Digital Humanities by creating a prototype of a repurposable platform that could be used as a simple tool to aggregate and search across any kind of digitised content available over IIIF (the [International Image Interoperability Framework](https://iiif.io/)), by scholars working on any kind of material, without the need for a high level of technical expertise, financial resources or institutional infrastructure.

## Installation

1. Clone the repository.
2. Create virtual environment in repository directory - "python -m venv venv".
3. Activate virtual environment from within repository directory - "source venv/bin/activate".
4. Install Python dependencies from requirements file - "pip install -r requirements.txt".
5. Create secret key for app security, see Secret Key section below.

## Using the Tool

### IIIF Manifest Extraction

1. Open terminal and navigate to root directory of tools.
2. Activate virtual environment as in installation instructions.
3. Navigate to "iiif_extraction/input/input.txt".
4. Insert a list of IIIF manifest URIs or IIIF collection URIs on individual lines within the file (there are examples of how they should appear within the file, delete these and add your own).
5. Navigate back to the "iiif_extraction" directory and run the following command - "python iiif_extractor.py".
6. This will extract the IIIF manifests for the URIs entered in the "input.txt" file. The manifests will be saved in the "outputs" directory.
7. The process of extraction may take a while, monitor the terminal for progress.
8. Successful manifest extraction and any errors in extraction process reported in the terminal.

### IIIF Flask Application

1. Open terminal and navigate to root directory of tools.
2. Activate virtual environment as in installation instructions.
3. Copy the files generated by the "iiif_extraction" script and move them to the "iiif_flask_app/files" directory. These manifest files be used to create the index for your application.
4. Navigate to "iiif_flask_app/config.py". This file forms the basis of the editable text and image sections of the application, together with some aspects of security.
5. Edit all of the sections of the "config.py" to fit the requirements of your application. Do not edit the "SECRET_KEY" variable as this will be generated separately, see Secret Key section below. Instructions for each section of the "Config.py" file are commented throughout, read the comments carefully and change the sections accordingly.
6. Navigate to the "iiif_flask_app" directory and run the following command - "python app.py".  
7. Open browser and navigate to "http://127.0.0.1:5000" to see the application in its current form.

## Secret Key

### Set up a secret key on macOS or Unix-like systems

1. Open terminal.
2. Identify shell type, Zsh or Bash.
    - run following command - "echo $SHELL"
3. Check for profile file.
    - if shell is Bash run "ls ~/.bashrc"
    - if shell is Zsh run "ls ~/.zshrc"
4. Create profile file in home directory if not there.
    - if shell is Bash run "touch ~/.bashrc"
    - if shell is Zsh run "touch ~/.zshrc"
5. Generate secret key.
    - run "python"
    - run "import secrets"
    - run "secrets.token_hex(16)"
    - copy the resulting token
6. Open profile file.
    - if shell is Bash run "nano ~/.bashrc"
    - if shell is Zsh run "nano ~/.zshrc"
7. Add secret key to file.
    - add a line to the file containing "export FLASK_SECRET_KEY=your generated key copied here"
    - Save and close the editor (Ctrl+X, then Y, then Enter for Nano editor)
8. Apply changes.
    - if shell is Bash run "source ~/.bashrc"
    - if shell is Zsh run "source ~/.zshrc"

### Set up a secret key on Windows (PowerShell)

1. Open Powershell terminal.
2. Check for profile file.
    - run the following command - "Test-Path $PROFILE"
3. Create profile file if not there.
    - run the following command - "if (-not (Test-Path $PROFILE)) {New-Item -Type File -Force $PROFILE}"
4. Generate secret key.
    - run "python"
    - run "import secrets"
    - run "secrets.token_hex(16)"
    - copy the resulting token
5. Open profile file.
    - run "notepad $PROFILE"
6. Add secret key to file.
    - add a line to the file containing "$Env:FLASK_SECRET_KEY=your generated key copied here"
    - Save and close Notepad
7. Apply changes.
    - run the following command - ". $PROFILE"
