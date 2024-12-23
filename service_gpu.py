from flask import Flask, request, jsonify
import transformers
import torch

model_id = "meta-llama/Llama-3.1-8B-Instruct"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.float32},
    device_map="auto",
)

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_string():
    # Get the long string from the request
    prompt = request.json.get('prompt', '')
    text = request.json.get('text', '')

    messages = [
    {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]

    outputs = pipeline(
        messages,
        max_new_tokens=1024,
    )
    result = outputs[0]["generated_text"][-1]

    return jsonify({'result': result['content']})

if __name__ == '__main__':
    app.run(debug=True, port=6001)
