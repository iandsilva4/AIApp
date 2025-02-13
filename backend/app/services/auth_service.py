from firebase_admin import auth

def verify_firebase_token(token):
    try:
        decoded_token = auth.verify_id_token(
            token,
            check_revoked=True,
            clock_skew_seconds=30
        )
        return decoded_token
    except auth.RevokedIdTokenError:
        return None
    except auth.InvalidIdTokenError:
        return None
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None 