from flask import Flask
import json

app = Flask(__name__)

with open('config.json') as config_file:
    config = json.load(config_file)
    
@app.route('/config')
def get_config():
    return config

@app.route('/')
def home():
    return "Hello, Flask is up and running!"

if __name__ == '__main__':
    app.run(debug=True)
