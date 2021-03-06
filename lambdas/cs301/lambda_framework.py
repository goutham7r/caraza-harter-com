import json, urllib, boto3, botocore, base64, time, traceback, random, string
from collections import defaultdict as ddict

ROUTES = {}
EXTRA_AUTH = ddict(list)
BUCKET = 'caraza-harter-cs301'
ADMIN_EMAIL = 'tylerharter@gmail.com'
INSTRUCTOR_EMAILS = ['tylerharter@gmail.com', 'adalbert.gerald@gmail.com']
GRADER_EMAILS = ['pivotlibre@gmail.com', 'szou28@wisc.edu', 'adalbert.gerald@gmail.com']

s3_cache = None # client

def s3():
    # cache S3 client
    global s3_cache
    if s3_cache == None:
        s3_cache = boto3.client('s3')
    return s3_cache

def s3_all_keys(Prefix):
    ls = s3().list_objects_v2(Bucket=BUCKET, Prefix=Prefix, MaxKeys=10000)
    keys = []
    while True:
        contents = [obj['Key'] for obj in ls.get('Contents',[])]
        keys.extend(contents)
        if not 'NextContinuationToken' in ls:
            break
        ls = s3.list_objects_v2(Bucket='caraza-harter-cs301', Prefix=Prefix,
                                ContinuationToken=ls['NextContinuationToken'],
                                MaxKeys=10000)
    return keys

def s3_path_exists(path):
    try:
        boto3.resource('s3').Object(BUCKET, path).load()
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise e

# decorators
def route(fn):
    ROUTES[fn.__name__] = fn
    return fn

# decorator: user must authenticate to the admin user
def admin(fn):
    EXTRA_AUTH[fn.__name__].append(admin_check)
    return fn

def instructor(fn):
    EXTRA_AUTH[fn.__name__].append(instructor_check)
    return fn

# decorator: user must authenticate and have a valid email
def user(fn):
    EXTRA_AUTH[fn.__name__].append(user_check)
    return fn

# decorator: user must authenticate and be a grader
def grader(fn):
    EXTRA_AUTH[fn.__name__].append(grader_check)
    return fn

def user_check(user):
    if user == None:
        raise Exception('could not authenticate user with google')
    if not user['email_verified']:
        raise Exception('google email not verified')

def admin_check(user):
    user_check(user)
    if user['email'] != ADMIN_EMAIL:
        raise Exception('admin permissions required')

def instructor_check(user):
    user_check(user)
    if not user['email'] in INSTRUCTOR_EMAILS:
        raise Exception('instructor permissions required')

def grader_check(user):
    user_check(user)
    if not user['email'] in GRADER_EMAILS:
        raise Exception('grader permissions required')

def is_grader(user):
    return user['email'] in GRADER_EMAILS

# TODO: cache this
def get_user(event):
    token = event['GoogleToken']
    req = urllib.request.Request('https://www.googleapis.com/oauth2/v3/tokeninfo?id_token='+token)
    response = urllib.request.urlopen(req)
    status = json.loads(response.read())
    return status

def error(message):
    return {
        "isBase64Encoded": False,
        "statusCode": 500,
        "headers": {},
        "body": message
    }

def save_user_info(user):
    path = 'users/google/%s.json' % user['sub']
    try:
        boto3.resource('s3').Object(BUCKET, path).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            # does not exist yet
            s3().put_object(Bucket=BUCKET,
                          Key=path,
                          Body=bytes(json.dumps(user, indent=2), 'utf-8'),
                          ContentType='text/json',
            )
        else:
            raise e
