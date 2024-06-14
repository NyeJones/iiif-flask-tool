# iiif-flask-app


## Installation

1. Clone the repository.
2. Create virtual environment in repository directory - "python -m venv venv"
3. Activate virtual environment from within repository directory - "source venv/bin/activate"
4. Install Python dependencies from requirements file - "pip install -r requirements.txt"
5. Create secret key for app security, instructions in Secret Key section below



## Secret Key

### Set up a secret key on macOS or Unix-like systems

1. Open terminal.
2. Identify shell type, Zsh or Bash.
- run following command - "echo $SHELL"
3. Check for profile file
- if shell is Bash run "ls ~/.bashrc"
- if shell is Zsh run "ls ~/.zshrc"
4. Create profile file in home directory if not there
- if shell is Bash run "touch ~/.bashrc"
- if shell is Zsh run "touch ~/.zshrc"
5. Generate secret key
- run "python"
- run "import secrets"
- run "secrets.token_hex(16)"
- copy the resulting token
6. Open profile file
- if shell is Bash run "nano ~/.bashrc"
- if shell is Zsh run "nano ~/.zshrc"
7. Add secret key to file
- add a line to the file containing "export FLASK_SECRET_KEY=your generated key copied here"
- Save and close the editor (Ctrl+X, then Y, then Enter for Nano editor).
8. Apply changes
- if shell is Bash run "source ~/.bashrc"
- if shell is Zsh run "source ~/.zshrc"

### Set up a secret key on Windows (PowerShell)

1. Open Powershell terminal.
2. Check for profile file
- run the following command - "Test-Path $PROFILE"
3. Create profile file if not there
- run the following command - "if (-not (Test-Path $PROFILE)) {New-Item -Type File -Force $PROFILE}"
4. Generate secret key
- run "python"
- run "import secrets"
- run "secrets.token_hex(16)"
- copy the resulting token
5. Open profile file
- run "notepad $PROFILE"
6. Add secret key to file
- add a line to the file containing "$Env:FLASK_SECRET_KEY=your generated key copied here"
- Save and close Notepad
7. Apply changes
- run the following command - ". $PROFILE"
