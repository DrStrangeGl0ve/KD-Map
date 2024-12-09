from flask import Flask, render_template, request, jsonify, send_file
import subprocess
from PIL import Image

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
        return jsonify(output=result.stdout, image_url='/generate-image')
    except Exception as e:
        return jsonify(error=str(e))

@app.route('/generate-image')
def generate_image():
    # Paths to images
    transparent_png_path = 'champion_kill_positions.png'
    summoners_rift_image_path = 'summoners_rift.png'
    output_image_path = 'static/overlaid_image.png'

    # Open and combine images
    base_image = Image.open(summoners_rift_image_path).convert("RGBA")
    overlay_image = Image.open(transparent_png_path).convert("RGBA")
    overlay_image = overlay_image.resize(base_image.size, Image.LANCZOS)
    combined_image = Image.alpha_composite(base_image, overlay_image)

    # Save and return the combined image
    combined_image.save(output_image_path)
    print(f"Overlaid image saved as {output_image_path}")
    return send_file(output_image_path, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)

