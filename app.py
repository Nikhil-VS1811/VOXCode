import os
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, abort

app = Flask(__name__, static_folder="static", template_folder="templates")

# Directory to save generated programs
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

# Whitelisted app names for macOS -> value is the app name passed to `open -a`
# Use the exact app display name as it appears in /Applications or Launchpad.
APP_WHITELIST = {
    "textedit": "TextEdit",
    "calculator": "Calculator",
    "vlc": "VLC",                     # install VideoLAN/VLC for this to work
    "chrome": "Google Chrome",        # Google Chrome
    "safari": "Safari",
    "terminal": "Terminal",
    # add more: "obs": "OBS" etc.
}

def app_exists_on_mac(app_name):
    """
    Quick check whether an app is discoverable by `open -Ra "AppName"`.
    Returns True if found, False otherwise.
    """
    try:
        # -R = reveal in Finder, -a = application, but when used together,
        # 'open -Ra' will return a non-zero exit code if the app can't be found.
        res = subprocess.run(["open", "-Ra", app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def open_app(app_name):
    """Try to open a whitelisted macOS application. Returns (success, message)."""
    key = app_name.lower().strip()
    if key not in APP_WHITELIST:
        return False, f"App '{app_name}' not whitelisted. Available: {', '.join(APP_WHITELIST.keys())}"
    mac_app_name = APP_WHITELIST[key]
    # Check existence first (best-effort)
    if not app_exists_on_mac(mac_app_name):
        return False, f"App '{mac_app_name}' not found on this Mac (looked for '{mac_app_name}'). Install or adjust APP_WHITELIST."
    try:
        # Use open -a "AppName" to launch macOS application
        subprocess.Popen(["open", "-a", mac_app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"Started '{mac_app_name}'."
    except Exception as e:
        return False, f"Failed to start '{mac_app_name}': {e}"

def generate_add_two_numbers(language="python", filename=None):
    """Generate a simple 'add two numbers' program. Returns (filename, source)."""
    if language.lower() == "python":
        src = (
            "def add(a, b):\n"
            "    return a + b\n\n"
            "if __name__ == '__main__':\n"
            "    a = int(input('Enter first number: '))\n"
            "    b = int(input('Enter second number: '))\n"
            "    print('Sum =', add(a, b))\n"
        )
        if not filename:
            filename = "add_two_numbers.py"
    elif language.lower() in ("c", "c++"):
        src = (
            '#include <stdio.h>\n\n'
            'int main(){\n'
            '    int a, b;\n'
            '    printf("Enter first number: "); scanf("%d", &a);\n'
            '    printf("Enter second number: "); scanf("%d", &b);\n'
            '    printf("Sum = %d\\n", a + b);\n'
            '    return 0;\n'
            '}\n'
        )
        filename = filename or "add_two_numbers.c"
    else:
        src = f"// Language {language} not supported yet.\n"
        filename = filename or f"add_two_numbers.txt"

    safe_path = os.path.join(GENERATED_DIR, filename)
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(src)
    return filename, src

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/command", methods=["POST"])
def command():
    """
    Receives JSON: { "text": "<recognized speech text>" }
    Returns JSON with { success, action, message, content? }
    """
    data = request.get_json(force=True)
    if not data or "text" not in data:
        return jsonify(success=False, message="No text provided."), 400

    text = data["text"].strip().lower()
    # Basic parsing: "open <app>" or "write program to add two numbers" etc.
    if text.startswith("open "):
        app_name = text[len("open "):].strip()
        ok, msg = open_app(app_name)
        return jsonify(success=ok, action="open_app", message=msg)

    if text.startswith("launch "):
        app_name = text[len("launch "):].strip()
        ok, msg = open_app(app_name)
        return jsonify(success=ok, action="open_app", message=msg)

    # detect "write program" or "create program" + what
    if "write program" in text or "create program" in text or text.startswith("write ") or text.startswith("create "):
        # handle simple pattern for adding two numbers
        if "add two numbers" in text or "add 2 numbers" in text or "add two numbers program" in text or ("add" in text and "numbers" in text):
            filename, src = generate_add_two_numbers(language="python")
            return jsonify(success=True, action="generate_program", message=f"Generated {filename}", filename=filename, source=src)
        else:
            # fallback: create a template file with the text as comment/instruction
            filename = "generated_program.txt"
            src = f"// USER REQUEST: {text}\n\n// TODO: implement the program described above.\n"
            safe_path = os.path.join(GENERATED_DIR, filename)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(src)
            return jsonify(success=True, action="generate_program", message=f"Generated {filename}", filename=filename, source=src)

    # other commands: run file? (disabled by default)
    if text.startswith("run "):
        fname = text[len("run "):].strip()
        path = os.path.join(GENERATED_DIR, fname)
        if not os.path.exists(path):
            return jsonify(success=False, action="run", message=f"File not found: {fname}")
        # SECURITY: do not auto-run arbitrary scripts. Offer to run if you explicitly enable it.
        return jsonify(success=False, action="run", message="Running files is disabled for safety. Ask to enable run with explicit consent.")

    # fallback — echo
    return jsonify(success=False, action="unknown", message=f"Could not parse command: '{text}'. Try 'open textedit' or 'write program to add two numbers'."), 400

@app.route("/generated/<path:filename>")
def download_generated(filename):
    # sanitize filename
    safe = os.path.normpath(filename)
    if safe.startswith(".."):
        abort(404)
    return send_from_directory(GENERATED_DIR, filename, as_attachment=True)

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

if __name__ == "__main__":
    print("Starting on http://127.0.0.1:5000 — run locally only.")
    # Bind to localhost only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
