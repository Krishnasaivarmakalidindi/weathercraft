"""
Netlify serverless function wrapper for Flask app
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app

# Create Flask app instance
app = create_app()


def handler(event, context):
    """
    Netlify function handler that wraps Flask WSGI app
    """
    from werkzeug.wrappers import Request, Response
    import base64
    
    # Parse the Netlify event into a WSGI-compatible request
    path = event.get('path', '/')
    method = event.get('httpMethod', 'GET')
    headers = event.get('headers', {})
    query_string = event.get('queryStringParameters', {})
    body = event.get('body', '')
    is_base64 = event.get('isBase64Encoded', False)
    
    if is_base64 and body:
        body = base64.b64decode(body).decode('utf-8')
    
    # Build query string
    qs = '&'.join([f"{k}={v}" for k, v in query_string.items()]) if query_string else ''
    
    # Create WSGI environ
    environ = {
        'REQUEST_METHOD': method,
        'SCRIPT_NAME': '',
        'PATH_INFO': path,
        'QUERY_STRING': qs,
        'CONTENT_TYPE': headers.get('content-type', ''),
        'CONTENT_LENGTH': str(len(body)) if body else '0',
        'SERVER_NAME': headers.get('host', 'localhost'),
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': None,
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }
    
    # Add headers to environ
    for key, value in headers.items():
        key = key.upper().replace('-', '_')
        if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            environ[f'HTTP_{key}'] = value
    
    # Handle request body
    if body:
        from io import BytesIO
        environ['wsgi.input'] = BytesIO(body.encode('utf-8'))
    
    # Get response from Flask app
    with app.request_context(environ):
        try:
            response = app.full_dispatch_request()
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': f'{{"error": "Internal Server Error: {str(e)}"}}',
            }
    
    # Convert Flask response to Netlify format
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True),
    }
