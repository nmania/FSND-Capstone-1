import json
from flask import request, _request_ctx_stack
from functools import wraps
from jose import jwt
from urllib.request import urlopen


AUTH0_DOMAIN = 'dev-eid5kfny.us.auth0.com'
ALGORITHMS = ['RS256']
API_AUDIENCE = 'stock'

## AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


## Auth Header

'''
@implement get_token_auth_header() method
    it should attempt to get the header from the request
        it should raise an AuthError if no header is present
    it should attempt to split bearer and the token
        it should raise an AuthError if the header is malformed
    return the token part of the header
'''
def get_token_auth_header():
    header=request.headers.get("Authorization", None)
    # raise AuthError if no header is present
    if not header:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header is missing.'
        }, 401)
    # if header is malformed, return the toekn part of the header
    header_split=header.split(' ')
    if header_split[0].lower()!='bearer' or len(header_split)!=2:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header is malformed.'
        }, 401)
    else:
        return header_split[1]

'''
@implement check_permissions(permission, payload) method
    @INPUTS
        permission: string permission (i.e. 'post:drink')
        payload: decoded jwt payload

    it should raise an AuthError if permissions are not included in the payload
        !!NOTE check your RBAC settings in Auth0
    it should raise an AuthError if the requested permission string is not in the payload permissions array
    return true otherwise
'''
def check_permissions(permission, payload):
    if 'permissions' not in payload:
        raise AuthError({
            'code': 'invalid_permission',
            'description': 'Permissions not included in payload'
        }, 400)
    elif permission not in payload['permissions']:
        raise AuthError({
            'code': 'unauthorized_permission',
            'description': ' Permission string not in the payload permissions array'
        }, 401)
    else:
        return True

'''
@implement verify_decode_jwt(token) method
    @INPUTS
        token: a json web token (string)

    it should be an Auth0 token with key id (kid)
    it should verify the token using Auth0 /.well-known/jwks.json
    it should decode the payload from the token
    it should validate the claims
    return the decoded payload

    !!NOTE urlopen has a common certificate error described here: https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
'''
# get RSA
def get_rsa(token):
    #get public key jwks
    url=f'http://{AUTH0_DOMAIN}/.well-known/jwks.json'
    jwks = json.loads(urlopen(url).read())
    
    # get data that is in the header
    unverified_header = jwt.get_unverified_header(token)

    # if key id 'kid' not in header, then error 
    if 'kid' not in unverified_header:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'key id missing in token header'
        }, 401)

     # if key id match, add the info to rsa_key
    rsa={}
    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
            break

    if not rsa:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Token header is malformed.'
        }, 401)
    
    return rsa

def verify_decode_jwt(token):
    rsa=get_rsa(token)
    try:
        payload = jwt.decode(
            token,
            rsa,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f'https://{AUTH0_DOMAIN}/'
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError({
            'code': 'token_expired',
            'description': 'Token expired.'
        }, 401)

    except jwt.JWTClaimsError:
        raise AuthError({
            'code': 'invalid_claims',
            'description': 'Incorrect claims. Please, check the audience and issuer.'
        }, 401)
    except Exception:
        raise AuthError({
            'code': 'invalid_token',
            'description': 'Unable to decode authentication token.'
        }, 400)

'''
@implement @requires_auth(permission) decorator method
    @INPUTS
        permission: string permission (i.e. 'post:drink')

    it should use the get_token_auth_header method to get the token
    it should use the verify_decode_jwt method to decode the jwt
    it should use the check_permissions method validate claims and check the requested permission
    return the decorator which passes the decoded payload to the decorated method
'''
def requires_auth(permission=''):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)

        return wrapper
    return requires_auth_decorator