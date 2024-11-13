from http.client import responses

import requests
import fire
import json
from requests_toolbelt import MultipartEncoder
import decrypt_repack

SERVER = ''
APPNAME = ''
API_KEY = ''
ADB_IDENTIFIER = ''
HASH = ''
DATA_HASH = ''
API_KEY_HEADERS = None


def start(server, apppath, api_key, identifier):
    """
    APK 정적/동적 분석 자동화 도구
    :param server: MobSF의 서버 주소 ex) http://127.0.0.1:8000
    :param apppath: 분석할 .apk 파일 ex) sample.apk
    :param api_key: MobSF의 API 키 ex) 414b2c503175858405a9c8f7caa58d0d9a0736f0958e9868812b8ff627e97917
    :param identifier: 안드로이드 가상머신 또는 실제 휴대폰의 주소 ex) 192.168.0.1:5555

    """
    global SERVER, APPNAME, API_KEY, ADB_IDENTIFIER, API_KEY_HEADERS, DATA_HASH
    SERVER = server
    APPNAME = apppath.split('/')[-1]
    API_KEY = api_key
    ADB_IDENTIFIER = {'identifier': identifier}
    API_KEY_HEADERS = {'Authorization': api_key}
    print("복호화 시작")
    decrypt = decrypt_repack
    APPNAME = decrypt.decrypt_and_repack(apppath, "dbcdcfghijklmaop")
    print(f"복호화 완료 APK{APPNAME}")
    data = upload()
    print("정적 분석 시작")
    scan(data)
    static_pdf()
    static_json()
    print("동적 분석 시작")
    mobsfy()
    start_dynamic_analysis()
    set_proxy()
    test_activity("exported")
    test_activity("activity")
    tls_test()
    dynamic_stop()
    dynamic_json()


def upload():
    global HASH, DATA_HASH
    print(f"{APPNAME} 업로드 시작")
    multipart_data = MultipartEncoder(fields={'file': (APPNAME, open(APPNAME, 'rb'), 'application/octet-stream')})
    headers = {'Content-Type': multipart_data.content_type, 'Authorization': API_KEY}
    response = requests.post(SERVER + '/api/v1/upload', data=multipart_data, headers=headers)
    if response.status_code != 200:
        print(f"{APPNAME} : {response.content}")
        exit(1)
    HASH = response.json()['hash']
    DATA_HASH = {"hash": HASH}
    print(f"업로드 됨. APK : {APPNAME}, Hash : {HASH}")
    return response.text


def scan(data):
    global DATA_HASH
    print("앱 스캔 시작 Hash : " + HASH)
    apk_info = json.loads(data)
    response = requests.post(SERVER + '/api/v1/scan', data=apk_info, headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"스캔 실패 {APPNAME} : {response.content}")
        exit(1)
    print("스캔 완료함.")


def static_pdf():
    print("정적 분석 결과를 PDF 파일로 생성 중")
    response = requests.post(SERVER + '/api/v1/download_pdf', data=DATA_HASH, headers=API_KEY_HEADERS, stream=True)
    if response.status_code != 200:
        print(f"파일 생성 실패 : {response.content}")
        exit(1)
    with open(f"{APPNAME}_{HASH}_static.pdf", "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    print(f"{APPNAME}_{HASH}_static.pdf로 파일이 생성됨.")



def static_json():
    print("정적 분석 결과를 JSON 파일로 생성 중")
    response = requests.post(SERVER + '/api/v1/report_json', data=DATA_HASH, headers=API_KEY_HEADERS, stream=True)
    if response.status_code != 200:
        print(f"파일 생성 실패 : {response.content}")
        exit(1)
    with open(f"{APPNAME}_{HASH}_static.json", "wb") as f:
        f.write(response.content)
    print(f"{APPNAME}_{HASH}_static.json로 파일이 생성됨")


def start_dynamic_analysis():
    print("동적 분석 하는중 ...")
    response = requests.post(SERVER + '/api/v1/dynamic/start_analysis', data=DATA_HASH, headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"동적 분석 실행 실패 : {response.content}")
        exit(1)
    print(f"동적 분석 시작 성공")


def set_proxy():
    print("프록시 설정 중")
    _set = {'action': 'set'}
    response = requests.post(SERVER + '/api/v1/android/global_proxy', data=_set, headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"프록시 설정 실패 : {response.content}")
        exit(1)
    print(f"프록시 설정 완료")

def mobsfy():
    print("안드로이드 환경 구축 중 ...")
    response = requests.post(SERVER + '/api/v1/android/mobsfy', data=ADB_IDENTIFIER,headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"환경 구축 실패 : {response.content}")
        exit(1)
    print("환경 구축 성공")

def test_activity(action):
    if action == "activity":
        print("Activity 시작")
    else:
        print(f"{action} Activity 테스트 시작")
    data = {"hash": HASH, "test": action}
    response = requests.post(SERVER + '/api/v1/android/activity', data=data, headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"Activity 테스트 실패 : {response.content}")
        exit(1)
    if action == "activity":
        print("Activity 테스트 성공")
    else:
        print(f"{action} Activity 테스트 성공")

def tls_test():
    print("TLS/SSL 테스트 시작")
    response = requests.post(SERVER + '/api/v1/android/tls_tests', data=DATA_HASH, headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"TLS/SSL 테스트 실패 : {response.content}")
        exit(1)
    print("TLS/SSL 성공")

def dynamic_stop():
    print("동적 분석 정지 중...")
    response = requests.post(SERVER + '/api/v1/dynamic/stop_analysis', data=DATA_HASH, headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"동적 분석 정지 실패 : {response.content}")
        exit(1)
    print("동적 분석 정지 완료")

def dynamic_json():
    print("동적 분석 결과를 JSON 파일로 생성 중...")
    response = requests.post(SERVER + '/api/v1/dynamic/report_json', data=DATA_HASH, headers=API_KEY_HEADERS)
    if response.status_code != 200:
        print(f"파일 생성 실패 : {response.content}")
        exit(1)
    with open(f"{APPNAME}_{HASH}_dynamic.json", "wb") as f:
        f.write(response.content)
    print(f"{APPNAME}_{HASH}_dynamic.json로 파일이 생성됨")


if __name__ == "__main__":
    fire.Fire(start)
