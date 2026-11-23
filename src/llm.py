import json
import requests


def chatWithModel(url, token, model, content, systemPrompt=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    messages = []
    if systemPrompt:
        messages.append({'role': 'system', 'content': systemPrompt})
    messages.append({'role': 'user', 'content': content})

    data = {
        'model': model,
        'messages': messages,
        'stream': False
    }

    response = requests.post(
        url + '/api/chat/completions', headers=headers, json=data
    )
    response.raise_for_status()

    # Some Open WebUI models ignore "stream": false and return an SSE stream
    # anyway, so handle both a single JSON body and an SSE stream.
    contentType = response.headers.get('Content-Type', '')
    if 'text/event-stream' in contentType or response.text.lstrip().startswith('data:'):
        parts = []
        for line in response.text.splitlines():
            line = line.strip()
            if not line.startswith('data:'):
                continue
            payload = line[len('data:'):].strip()
            if payload == '[DONE]':
                break
            chunk = json.loads(payload)
            delta = chunk['choices'][0].get('delta', {})
            if delta.get('content'):
                parts.append(delta['content'])
        return ''.join(parts)

    return response.json()['choices'][0]['message']['content']
