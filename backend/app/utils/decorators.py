from functools import wraps
from flask import request, jsonify
import firebase_admin.auth

def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        try:
            # Remove 'Bearer ' from the token
            token = auth_header.split(' ')[1]
            # Verify the token
            decoded_token = firebase_admin.auth.verify_id_token(token)
            user_email = decoded_token.get('email')
            
            if not user_email:
                return jsonify({'error': 'No email in token'}), 401

            return f(user_email=user_email, *args, **kwargs)

        except IndexError:
            return jsonify({'error': 'Invalid authorization header format'}), 401
        except firebase_admin.auth.InvalidIdTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            print(f"Authentication Error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401

    return decorated_function