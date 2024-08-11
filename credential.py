import boto3
from dotenv import load_dotenv
import os

# SSM region
REGION = 'ap-northeast-1'
CALENDAR_APP_PREFIX = '/AIBOS-CALENDAR/'

def get_parameters(param_key):
    try:
        
        return get_parameters(param_key)
    except:
        print("failed to get parameters from aws")
        return os.environ.get(param_key, 'can not get cledential')
    

# awsの情報が取得できる時は、それを使う
# awsの情報が使えない時は環境変数を使う。
def aws_get_parameters(param_key):
    ssm = boto3.client('ssm', region_name=REGION)
    response = ssm.get_parameters(
        Names=[
            CALENDAR_APP_PREFIX + param_key,
        ],
        WithDecryption=True
    )
    return response['Parameters'][0]['Value']