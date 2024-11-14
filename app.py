from flask import Flask, render_template, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_script', methods=['POST'])
def run_script():
    game_name = request.form['gameName']
    tag_name = request.form['tagName']
    count = request.form['count']
    
    try:
        # Run game_data.py
        result = subprocess.run(['python3', 'game_data.py', game_name, tag_name, count], capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify(error=result.stderr)

        # Return JSON with the output and image path
        return jsonify(output=result.stdout, image_url='/static/overlaid_image.png')
    except Exception as e:
        return jsonify(error=str(e))

if __name__ == '__main__':
    app.run(debug=True)