import os
import sys
import boto3
import requests
import base64
from nacl import encoding, public

GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_REPOSITORY = os.environ['GITHUB_REPOSITORY']
IAM_USER_NAME = "git-docker"
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

def list_access_keys(iam_user):
    iam = boto3.client('iam',
                       aws_access_key_id=AWS_ACCESS_KEY_ID,
                       aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    response = iam.list_access_keys(UserName=iam_user)
    return response['AccessKeyMetadata']

def find_active_keys(keys):
    return [k for k in keys if k['Status'] == 'Active']

def deactivate_old_key(iam_user, key_id):
    iam = boto3.client('iam',
                       aws_access_key_id=AWS_ACCESS_KEY_ID,
                       aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    try:
        iam.update_access_key(UserName=iam_user,
                             AccessKeyId=key_id,
                             Status='Inactive')
        print(f"Deactivated old access key: {key_id}")
    except Exception as e:
        print(f"Failed to deactivate key: {key_id}. Error: {e}")

def create_new_key(iam_user):
    iam = boto3.client('iam',
                       aws_access_key_id=AWS_ACCESS_KEY_ID,
                       aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    response = iam.create_access_key(UserName=iam_user)
    new_key = response['AccessKey']
    return new_key['AccessKeyId'], new_key['SecretAccessKey']

def get_repo_public_key():
    api_url = f'https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/secrets/public-key'
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()

def encrypt_secret(public_key, secret_value):
    key = public.PublicKey(public_key.encode('utf-8'), encoding.Base64Encoder())
    sealed_box = public.SealedBox(key)
    encrypted = sealed_box.encrypt(secret_value.encode('utf-8'))
    return base64.b64encode(encrypted).decode('utf-8')

def put_github_secret(secret_name, encrypted, key_id):
    api_url = f'https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/secrets/{secret_name}'
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    payload = {
        "encrypted_value": encrypted,
        "key_id": key_id
    }
    response = requests.put(api_url, headers=headers, json=payload)
    response.raise_for_status()

def main():
    print("Listing current AWS access keys...")
    keys = list_access_keys(IAM_USER_NAME)
    active_keys = find_active_keys(keys)
    print(f"Found {len(keys)} total keys, {len(active_keys)} active key(s).")

    if len(keys) >= 2:
        print("Error: Two or more access keys found for this user. Deployment should fail.")
        sys.exit(1)

    if len(active_keys) == 1:
        print("One active access key found. Deactivating...")
        deactivate_old_key(IAM_USER_NAME, active_keys[0]['AccessKeyId'])
    else:
        print("No active access key found. Proceeding to create new key...")

    print("Creating new AWS key...")
    new_access_key_id, new_secret_access_key = create_new_key(IAM_USER_NAME)

    print("Getting GitHub repo public key for secrets...")
    public_key_obj = get_repo_public_key()
    public_key = public_key_obj['key']
    key_id = public_key_obj['key_id']

    print("Encrypting and storing new AWS_ACCESS_KEY_ID in GitHub...")
    encrypted_akid = encrypt_secret(public_key, new_access_key_id)
    put_github_secret("AWS_ACCESS_KEY_ID", encrypted_akid, key_id)

    print("Encrypting and storing new AWS_SECRET_ACCESS_KEY in GitHub...")
    encrypted_sak = encrypt_secret(public_key, new_secret_access_key)
    put_github_secret("AWS_SECRET_ACCESS_KEY", encrypted_sak, key_id)

    print("Credential rotation complete.")

if __name__ == "__main__":
    main()
