# iiif-flask-tool

This tool aims to solve a general problem in the __Digital Humanities__ by creating a prototype of a repurposable platform that can be used as a simple tool to aggregate and search across any kind of digitised content available over __IIIF__ (the [International Image Interoperability Framework](https://iiif.io/)), by scholars working on any kind of material, without the need for a high level of technical expertise, financial resources or institutional infrastructure.

Instructions are for both __MacOs/Unix-like__ and __Windows__ systems. 

__Please note that Windows Powershell processes sometimes need to be finished by pressing enter__.

## Secret Key

We begin by setting up a __secret key__ that will be used to enhance site security. Instructions for __MacOs/Unix-like__ and __Windows__ systems are below, please follow the appropriate instructions. When you have finished, move on to the __Installation__ section. 

### Set up a secret key on macOS or Unix-like systems

1. Open __terminal__.
2. Identify shell type, __Bash__ or __Zsh__ by running the following command:
```
echo $SHELL
```

3. Check if profile file exists, run one of following commands for __Bash__ or __Zsh__ shells respectively:
```
ls ~/.bashrc
ls ~/.zshrc
```

4. Create __profile__ file in __home__ directory if not there, run one of following commands for __Bash__ or __Zsh__ shells respectively:
```
touch ~/.bashrc
touch ~/.zshrc
```

5. Generate __secret key__ token by using following commands:
```
python
import secrets
secrets.token_hex(16)
```

Copy the resulting token, then exit Python with the following command:

```
exit()
```

6. Open __profile__ file by running one of following commands for __Bash__ or __Zsh__ shells respectively:
```
nano ~/.bashrc
nano ~/.zshrc
```

7. Add __secret key__ to __profile__ file by adding the following line to the file, pasting the token generated earlier between the quotation marks:
```
export IIIF_FLASK_KEY="your generated key copied here"
```
Then __save__ and __close__ the editor (Ctrl+X, then Y, then Enter for Nano editor).

8. __Apply changes__ by running one of following commands for __Bash__ or __Zsh__ shells respectively:
``` 
source ~/.bashrc
source ~/.zshrc
```

### Set up a secret key on Windows

1. Open __Powershell__ terminal.
2. Generate __secret key__ token by using following commands:
```
python
import secrets
secrets.token_hex(16)
```

Copy the resulting token, then exit Python with the following command:

```
exit()
```

3. Exit the __Powershell__ terminal and use the following instructions on __desktop__.
4. Open the __Control Panel__.
5. Go to __System and Security__.
6. Click on __System__.
7. Select __Advanced system settings__ on the left side.
8. In the __System Properties__ window, click on the __Environment Variables__ button.
9. In the __User variables__ section, click on the __New..__ button.
10. In the __New User Variable__ window, enter __IIIF_FLASK_KEY__ in the __Variable name__ field and your copied __secret key token__ in the __Variable value__ field, keeping the quotation marks, and click on the __OK__ button.
11. Finally, click on the __OK__ button in the __Environment Variables__ window.

# Installation

Having created a __secret key__, we are now in a position to install the tool. Instructions for __MacOs/Unix-like__ and __Windows__ systems are below, please follow the appropriate instructions. When you have finished, move on to the __Using the Tool__ section. 

## Installation on macOS or Unix-like systems

1. __Clone__ or __download__ the __repository__ on your computer.
2. Open __terminal__ and navigate to the __repository__ directory. 
3. Create __virtual environment__ in __repository__ directory:
```
python -m venv venv
```

4. Activate __virtual environment__ from within __repository__ directory:
``` 
source venv/bin/activate
```

5. Install __Python dependencies__ from __requirements__ file:
```
pip install -r requirements.txt
```

## Installation on Windows (PowerShell)

1. __Clone__ or __download__ the repository on your computer.
2. Open __Powershell__ terminal and navigate to the __repository__ directory.
3. Create __virtual environment__ in __repository__ directory:
```
python -m venv venv
```

4. Activate __virtual environment__ from within __repository__ directory:
``` 
.\venv\Scripts\activate
```

5. Install __Python dependencies__ from __requirements__ file:
```
pip install -r requirements.txt
```

## Using the Tool

The tool is divided into __two main parts__. The first part extracts __IIIF manifests__ using an __input file__ containing a list of __IIIF URIs__. The second part uses these __IIIF manifests__ to create an __editable website__ using __Python__ and __Flask__, which is __run locally__ on your computer. This website is then ready to be moved from the local host to the __server provider__ of your choice.

The __Flask backend__ ensures robust __security__ through comprehensive measures such as protection against __Cross-Site Scripting (XSS)__ and __Cross-Site Request Forgery (CSRF)__, and the implementation of __security headers__ like __Content Security Policy (CSP)__, __HTTP Strict Transport Security (HSTS)__, and __X-Content-Type-Options__.

### IIIF Manifest Extraction

1. Navigate to the __input.txt__ file:
```
iiif_extraction/input/input.txt
```

2. Insert a list of __IIIF manifest URIs__ or __IIIF collection URIs__ on individual lines within the file. Examples of how they should appear can be found in the file, __delete these and add your own__.
3. Open __terminal__ for MacOs/Unix-like or __Powershell__ for Windows and navigate to the __repository__ directory.
4. Activate __virtual environment__ as per installation instructions.
5. Navigate back to the __iiif_extraction__ directory and run the following command to run the __manifest extraction__ code:
```
python iiif_extractor.py
```

6. This will extract the __IIIF manifests__ for the URIs entered in the __input.txt__ file. The manifests will be saved in the __outputs__ directory.
7. The process of extraction may take a while, __monitor terminal__ for progress.
8. Successful manifest extraction and any errors in extraction process __reported in the terminal__.

### IIIF Flask Application

1. Copy the files generated in __iiif_extraction/outputs__ by the __iiif_extraction__ script and move them to the __iiif_flask_app/files__ directory. These manifest files will be used to create the __index__ for your application.
2. Navigate to __iiif_flask_app/config.py__ and open it in an editor. This file forms the basis of the __editable text and image__ sections of the application, together with some aspects of __security__.
3. Edit the sections of __config.py__ to fit the requirements of your application. Do not edit the __SECRET_KEY__ variable as this will be generated separately, see __Secret Key__ sections above. Instructions for each section of the __config.py__ file are commented throughout, __read the comments carefully and change the sections accordingly__.
4. Open __terminal__ and navigate to the __repository__ directory.
5. Activate __virtual environment__ as per installation instructions.
6. Navigate to the __iiif_flask_app__ directory and run the following command:
```
python app.py
```

7. Open __browser__ and navigate to the __following url__ to run the application locally on your computer:
```
http://127.0.0.1:5000
```
