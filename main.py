import json
import random
import secrets
import string
import threading
import uuid
import logging
from os import system
from time import time
from hashlib import md5
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from threading import Thread, Lock
from urllib.parse import urlencode
import requests
from utils.email_api import RamblerIMAPEmail
from signer.sign import sign
import pytz
import pycountry
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

lock = threading.Lock()

@dataclass
class Config:
    VERSION_LIST = ['43.1.1'] # Get from https://www.apkmirror.com/apk/tiktok-pte-ltd/tik-tok-including-musical-ly/
    DOMAINS = [
        "api16-normal-alisg.tiktokv.com",
        "api16-normal-c-alisg.tiktokv.com",
        "api31-normal-alisg.tiktokv.com",
        "api16-normal-c-useast1a.tiktokv.com",
        "api22-normal-c-useast1a.tiktokv.com",
        "api16-normal-c-useast1a.musical.ly",
        "api19-normal-c-useast1a.musical.ly",
        "api.tiktokv.com"
    ]

@dataclass
class Device:
    iid: str
    did: str
    device_type: str
    device_brand: str
    os_version: str
    cdid: str
    openudid: str
    version: str
    sec_token: str
    country: str

    def to_dict(self) -> Dict:
        return {
            'iid': self.iid,
            'did': self.did,
            'device_type': self.device_type,
            'device_brand': self.device_brand,
            'os_version': self.os_version,
            'cdid': self.cdid,
            'openudid': self.openudid,
            'version': self.version,
            'sec_token': self.sec_token,
            'country': self.country
        }

class TikTokAPI:
    def __init__(self, proxy: str):
        self.proxy = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        self.session = requests.Session()
        self.session.proxies.update(self.proxy)

    @staticmethod
    def xor(value: str) -> str:
        return "".join([hex(ord(c) ^ 5)[2:] for c in value])

    @staticmethod
    def build_params(device: Device) -> Dict:
        version_code = device.version.replace('.', '0')
        timestamp = str(time() * 1000)[:13]
        timestamp_sec = str(time() * 1000)[:10]
        
        return {
            'passport-sdk-version': '19',
            'iid': device.iid,
            'device_id': device.did,
            'ac': 'wifi',
            'channel': 'googleplay',
            'aid': '1233',
            'app_name': 'musical_ly',
            'version_code': version_code,
            'version_name': device.version,
            'device_platform': 'android',
            'os': 'android',
            'ab_version': device.version,
            'ssmix': 'a',
            'device_type': device.device_type,
            'device_brand': device.device_brand,
            'language': device.country.lower(),
            'os_api': '25',
            'os_version': device.os_version,
            'openudid': device.openudid,
            'manifest_version_code': f'202{version_code}0',
            'resolution': '1467*720',
            'dpi': '300',
            'update_version_code': f'202{version_code}0',
            '_rticket': timestamp,
            'is_pad': '0',
            'app_type': 'normal',
            'sys_region': device.country.upper(),
            'mcc_mnc': '50514',
            'timezone_name': random.choice(pytz.all_timezones),
            'ts': timestamp_sec,
            'timezone_offset': '-37800',
            'build_number': device.version,
            'region': device.country.upper(),
            'carrier_region': device.country.upper(),
            'uoo': '0',
            'app_language': device.country.lower(),
            'op_region': device.country.upper(),
            'ac2': 'wifi',
            'host_abi': 'armeabi-v7a',
            'cdid': device.cdid,
            'support_webview': '1',
            'reg_store_region': device.country.lower(),
            'okhttp_version': '4.2.137.40-tiktok',
            'use_store_region_cookie': '1'
        }

    @staticmethod
    def build_headers(device: Device, payload: str, sig: dict, dm_status: str = "login=0;ct=0;rt=9") -> Dict:
        version_code = device.version.replace('.', '0')
        
        x_ladon = sig.get('x-ladon') or sig.get('X-Ladon', '')
        x_khronos = sig.get('x-khronos') or sig.get('X-Khronos', '')
        x_argus = sig.get('x-argus') or sig.get('X-Argus', '')
        x_gorgon = sig.get('x-gorgon') or sig.get('X-Gorgon', '')
        x_ss_stub = sig.get('x-ss-stub') or sig.get('X-SS-Stub', '') or md5(payload.encode('utf-8')).hexdigest().upper()
        x_ss_req_ticket = sig.get('x-ss-req-ticket') or sig.get('X-SS-Req-Ticket', '') or str(time() * 1000)[:13]
        
        return {
            'accept-encoding': 'gzip',
            'connection': 'Keep-Alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'passport-sdk-version': '19',
            'sdk-version': '2',
            'user-agent': f'com.zhiliaoapp.musically/202{version_code}0 (Linux; U; Android {device.os_version}; en_{device.country.upper()}; {device.device_type}; Build/RP1A.200720.012;tt-ok/3.12.13.4-tiktok)',
            'x-ss-req-ticket': x_ss_req_ticket,
            'x-ss-stub': x_ss_stub,
            'x-tt-bypass-dp': '1',
            'x-tt-dm-status': dm_status,
            'x-vc-bdturing-sdk-version': '2.3.4.i18n',
            'x-ladon': x_ladon,
            'x-khronos': str(x_khronos),
            'x-argus': x_argus,
            'x-gorgon': x_gorgon
        }

    def send_code(self, domain: str, email: str, password: str, device: Device) -> Tuple[requests.Response, str]:
        params = self.build_params(device)
        params_str = urlencode(params)

        payload_data = {
            'password': self.xor(password),
            'rule_strategies': '2',
            'mix_mode': '1',
            'multi_login': '1',
            'email': self.xor(email),
            'account_sdk_source': 'app',
            'type': '34'
        }
        payload = urlencode(payload_data)

        sig = sign(params_str, payload, device.sec_token, None, 1233)
        headers = self.build_headers(device, payload, sig)

        response = self.session.post(f'https://{domain}/passport/email/send_code/?{params_str}', headers=headers, data=payload)
        return response, params_str

    def verify_code(self, domain: str, email: str, code: str, device: Device) -> requests.Response:
        params = self.build_params(device)
        params_str = urlencode(params)

        payload_data = {
            'birthday': f"{random.randint(1965, 2008)}-0{random.randint(1, 12)}-{random.randint(1, 28)}",
            'code': code,
            'account_sdk_source': 'app',
            'mix_mode': '1',
            'multi_login': '1',
            'type': '34',
            'email': self.xor(email)
        }
        payload = urlencode(payload_data)

        url = f'https://{domain}/passport/email/register_verify_login/?{params_str}'
        sig = sign(params_str, payload, device.sec_token, None, 1233)
        headers = self.build_headers(device, payload, sig, dm_status="login=1;ct=1;rt=8")

        response = self.session.post(url, headers=headers, data=payload)
        return response

class DeviceGenerator:
    """Dynamic device generator that registers devices with TikTok API"""
    
    def __init__(self, region: str = "US", proxy: str = None):
        self.device_models = {
            "Samsung": ["SM-G9900", "SM-G950F", "SM-A136U1", "SM-M225FV", "SM-E426B", "SM-M526BR", "SM-M326B", "SM-A528B", "SM-F711B", "SM-F926B", "SM-A037G", "SM-A225F", "SM-M325FV", "SM-A226B", "SM-M426B", "SM-A525F", "SM-S901E", "SM-S908E", "SM-F936B", "SM-A536E"],
            "OnePlus": ["NE2211", "NE2215", "LE2121", "LE2125", "IN2013", "IN2025", "GM1913", "GM1917", "HD1913", "KB2003"],
            "Xiaomi": ["2201123G", "2107113SG", "2203129G", "2109119DG", "22081212UG", "21121119SG", "2201117TY", "21091116AG", "2201122C", "21071110C"],
            "Huawei": ["NOH-NX9", "TET-AN00", "ANA-AN00", "JAD-AL00", "LIO-AL00", "EBG-AN00", "OCE-AN10", "VOG-AL00", "ELE-AL00", "MAR-AL00"],
            "Motorola": ["XT2141-2", "XT2201-2", "XT2175-2", "XT2153-1", "XT2091-4", "XT2113-2", "XT2125-4", "XT2135-2", "XT2045-4", "XT2052-2"],
            "Google": ["GP4BC", "G9B9U", "G1AZG", "GB7N6", "GE2AE", "GZPF0", "GPJ41", "GTS4L", "GB62Z", "G0NZ6"],
            "Oppo": ["CPH2371", "CPH2357", "CPH2343", "CPH2325", "CPH2305", "CPH2249", "CPH2237", "CPH2219", "CPH2205", "CPH2173"]
        }
        self.region = region
        self.current_time_ms = int(time() * 1000)
        self.current_time_s = int(time())
        self.device_manufacturer = random.choice(list(self.device_models.keys()))
        self.device_model = random.choice(self.device_models[self.device_manufacturer])
        self.device_brand = self.device_manufacturer
        self.proxy = proxy
    
    def _get_proxies(self):
        if self.proxy:
            return {"http": f"http://{self.proxy}", "https": f"http://{self.proxy}"}
        return {}
    
    def _generate_device_header(self) -> Dict[str, Any]:
        android_versions = {"Samsung": [11, 12, 13, 14], "OnePlus": [11, 12, 13, 14], "Xiaomi": [11, 12, 13, 14], "Huawei": [10, 11, 12], "Motorola": [11, 12, 13], "Google": [13, 14, 15], "Oppo": [11, 12, 13]}
        os_version = str(random.choice(android_versions.get(self.device_manufacturer, [11, 12, 13])))
        os_api = {"9": 28, "10": 29, "11": 30, "12": 31, "13": 33, "14": 34, "15": 35}.get(os_version, 30)
        
        return {
            "header": {
                "os": "Android", "os_version": os_version, "os_api": os_api, "device_model": self.device_model,
                "device_brand": self.device_brand, "device_manufacturer": self.device_manufacturer, "cpu_abi": "arm64-v8a",
                "density_dpi": random.choice([240, 320, 420, 480, 560]), "display_density": random.choice(["mdpi", "hdpi", "xhdpi", "xxhdpi"]),
                "resolution": random.choice(["1080x1920", "1440x2560", "720x1280"]), "display_density_v2": random.choice(["hdpi", "xhdpi", "xxhdpi"]),
                "resolution_v2": random.choice(["1920x1080", "2560x1440", "1280x720"]), "access": "wifi",
                "rom": f"{self.device_manufacturer[:1].upper()}.c{random.randint(100000,999999)}-{random.randint(1,99)}_{random.randint(10,99)}f",
                "rom_version": f"{self.device_model}_{random.randint(10,99)}_C.{random.randint(10,99)}", "language": random.choice(["en", "ar", "fr", "es", "de", "pt"]),
                "timezone": random.randint(1, 12), "tz_name": random.choice(["Asia/Baghdad", "America/New_York", "Europe/London", "Asia/Dubai"]),
                "tz_offset": random.choice([10800, 14400, 18000, -14400, -18000]), "sim_region": self.region.lower(),
                "carrier": random.choice(["AT&T", "Verizon", "T-Mobile", "Vodafone", "Orange"]), "mcc_mnc": random.choice(["310410", "310260", "310160", "23415", "26201"]),
                "clientudid": str(uuid.uuid4()), "openudid": str(uuid.uuid4().hex), "channel": "googleplay", "not_request_sender": 1, "aid": 1233,
                "release_build": f"{uuid.uuid4().hex[:7]}_{random.randint(20230000,20249999)}", "ab_version": "40.7.3", "gaid_limited": 0,
                "custom": {"ram_size": random.choice(["4GB", "6GB", "8GB", "12GB"]), "dark_mode_setting_value": random.choice([0, 1]), "is_foldable": 0,
                "screen_height_dp": random.choice([800, 1067, 1200, 1440]), "apk_last_update_time": self.current_time_ms, "filter_warn": 0,
                "priority_region": self.region, "user_period": 0, "is_kids_mode": 0, "web_ua": f"Dalvik/2.1.0 (Linux; U; Android {os_version}; {self.device_model} Build/{uuid.uuid4().hex[:8].upper()})",
                "screen_width_dp": random.choice([480, 648, 720, 900]), "user_mode": -1}, "package": "com.zhiliaoapp.musically", "app_version": "40.7.3",
                "app_version_minor": "", "version_code": 400703, "update_version_code": 2024007030, "manifest_version_code": 2024007030,
                "app_name": "musical_ly", "tweaked_channel": "googleplay", "display_name": "TikTok", "sig_hash": uuid.uuid4().hex, "cdid": str(uuid.uuid4()),
                "device_platform": "android", "git_hash": uuid.uuid4().hex[:7], "sdk_version_code": 2050990, "sdk_target_version": 30, "req_id": str(uuid.uuid4()),
                "sdk_version": "2.5.9", "guest_mode": 0, "sdk_flavor": "i18nInner", "apk_first_install_time": self.current_time_ms, "is_system_app": 0
            }, "magic_tag": "ss_app_log", "_gen_time": self.current_time_ms
        }
    
    def _generate_params(self, header: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "req_id": header["header"]["req_id"], "device_platform": header["header"]["device_platform"], "os": header["header"]["os"].lower(), "ssmix": "a",
            "_rticket": str(self.current_time_ms), "cdid": header["header"]["cdid"], "channel": header["header"]["channel"], "aid": str(header["header"]["aid"]),
            "app_name": header["header"]["app_name"], "version_code": str(header["header"]["version_code"]), "version_name": header["header"]["app_version"],
            "manifest_version_code": str(header["header"]["manifest_version_code"]), "update_version_code": str(header["header"]["update_version_code"]),
            "ab_version": header["header"]["ab_version"], "resolution": header["header"]["resolution_v2"].replace("x", "*"), "dpi": str(header["header"]["density_dpi"]),
            "device_type": header["header"]["device_model"], "device_brand": header["header"]["device_brand"], "language": header["header"]["language"],
            "os_api": str(header["header"]["os_api"]), "os_version": header["header"]["os_version"], "ac": header["header"]["access"], "is_pad": "0",
            "app_type": "normal", "sys_region": self.region, "last_install_time": str(self.current_time_s), "mcc_mnc": header["header"]["mcc_mnc"],
            "timezone_name": header["header"]["tz_name"], "carrier_region_v2": header["header"]["mcc_mnc"][:3], "app_language": header["header"]["language"],
            "carrier_region": self.region, "timezone_offset": str(header["header"]["tz_offset"]), "host_abi": header["header"]["cpu_abi"],
            "locale": header["header"]["language"], "ac2": "unknown", "uoo": "1", "op_region": self.region, "build_number": header["header"]["app_version"],
            "region": self.region, "ts": str(self.current_time_s), "openudid": header["header"]["openudid"], "okhttp_version": "4.2.228.19-tiktok",
            "use_store_region_cookie": "1",
        }
    
    def _generate_headers(self, header: Dict[str, Any]) -> Dict[str, str]:
        return {
            'User-Agent': f"com.zhiliaoapp.musically/2024007030 (Linux; U; Android {header['header']['os_version']}; {header['header']['language']}; {header['header']['device_model']}; Build/{uuid.uuid4().hex[:8].upper()};tt-ok/3.12.13.20)",
            'Accept-Encoding': "gzip", 'Content-Type': "application/json",
            'x-tt-app-init-region': f"carrierregion={self.region};mccmnc={header['header']['mcc_mnc']};sysregion={self.region};appregion={self.region}",
            'x-tt-request-tag': "t=0;n=1", 'x-tt-dm-status': "login=0;ct=0;rt=7", 'sdk-version': "2", 'passport-sdk-version': "-1",
            'x-vc-bdturing-sdk-version': "2.3.13.i18n", 'content-type': "application/json; charset=utf-8"
        }

    def _register_device(self, payload: Dict[str, Any], params: Dict[str, Any], headers: Dict[str, str]) -> Optional[Dict[str, str]]:
        url = "https://log-boot.tiktokv.com/service/2/device_register/"
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, params=params, timeout=30, proxies=self._get_proxies())
            response.raise_for_status()
            data = response.json()
            device_id = data.get("device_id_str")
            iid = data.get("install_id_str")
            if device_id and iid:
                return {"device_id": device_id, "install_id": iid}
        except Exception as e:
            logger.debug(f"Device registration error: {e}")
        return None

    def _prepare_signing_data(self, params: Dict[str, Any], cookies: Dict[str, str], payload: Dict[str, Any]) -> tuple:
        params_str = urlencode(params)
        cookies_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)
        return params_str, cookies_str, payload_str

    def _verify_device(self, device_info: Dict[str, str], header: Dict[str, Any], base_headers: Dict[str, str]) -> bool:
        url = "https://api16-normal-useast5.tiktokv.us/consent/api/record/create/sync/v2"
        params = {
            "device_platform": header["header"]["device_platform"], "os": header["header"]["os"].lower(), "ssmix": "a",
            "_rticket": str(int(time() * 1000)), "channel": header["header"]["channel"], "aid": str(header["header"]["aid"]),
            "app_name": header["header"]["app_name"], "version_code": str(header["header"]["version_code"]), "version_name": header["header"]["app_version"],
            "manifest_version_code": str(header["header"]["manifest_version_code"]), "update_version_code": str(header["header"]["update_version_code"]),
            "ab_version": header["header"]["ab_version"], "resolution": header["header"]["resolution_v2"].replace("x", "*"), "dpi": str(header["header"]["density_dpi"]),
            "device_type": header["header"]["device_model"], "device_brand": header["header"]["device_brand"], "language": header["header"]["language"],
            "os_api": str(header["header"]["os_api"]), "os_version": header["header"]["os_version"], "ac": header["header"]["access"], "is_pad": "0",
            "app_type": "normal", "sys_region": self.region, "last_install_time": str(self.current_time_s), "mcc_mnc": header["header"]["mcc_mnc"],
            "timezone_name": header["header"]["tz_name"], "carrier_region_v2": self.region, "app_language": header["header"]["language"],
            "carrier_region": self.region, "timezone_offset": str(header["header"]["tz_offset"]), "host_abi": header["header"]["cpu_abi"],
            "locale": header["header"]["language"], "ac2": header["header"]["access"], "uoo": "0", "op_region": self.region,
            "build_number": header["header"]["app_version"], "region": self.region, "ts": int(time()), "iid": device_info["install_id"],
            "device_id": device_info["device_id"], "app_version": "40.7.3"
        }
        tokens = secrets.token_hex(16)
        cookies_dict = {"passport_csrf_token": tokens, "passport_csrf_token_default": tokens}
        consent_payload = {'consent_records': "[{\"flow\":\"consent_box\",\"entity_key\":\"conditions-policy-device-consent\",\"status\":1}]", 'sdk_version': "2.7.4.4", 'sdk_name': "pns_consent_sdk"}
        
        try:
            params_str, cookies_str, payload_str = self._prepare_signing_data(params, cookies_dict, consent_payload)
            try:
                signed_data = sign(params=params_str, cookie=cookies_str, payload=payload_str)
            except TypeError:
                try:
                    signed_data = sign(params=params, cookie=cookies_dict, payload=consent_payload)
                except:
                    signed_data = sign(params=params)
            
            verification_headers = {
                'User-Agent': base_headers['User-Agent'], 'Accept-Encoding': "gzip", 'rpc-persist-pyxis-policy-v-tnc': "1",
                'x-ss-stub': signed_data.get('x-ss-stub', ''), 'x-tt-pba-enable': "1", 'sdk-version': "2", 'x-tt-dm-status': "login=0;ct=1;rt=6",
                'x-ss-req-ticket': signed_data.get('x-ss-req-ticket', ''), 'passport-sdk-version': "-1", 'rpc-persist-pns-region-1': "US|6252001",
                'rpc-persist-pns-region-2': "US|6252001", 'rpc-persist-pns-region-3': "US|6252001", 'x-vc-bdturing-sdk-version': "2.3.13.i18n",
                'oec-vc-sdk-version': "3.0.12.i18n", 'x-tt-store-region': "us", 'x-tt-store-region-src': "did", 'x-ladon': signed_data.get('x-ladon', ''),
                'x-khronos': signed_data.get('x-khronos', ''), 'x-argus': signed_data.get('x-argus', ''), 'x-gorgon': signed_data.get('x-gorgon', '')
            }
            verification_headers = {k: v for k, v in verification_headers.items() if v}
            response = requests.post(url, data=consent_payload, headers=verification_headers, cookies=cookies_dict, params=params, timeout=30, proxies=self._get_proxies())
            return "device_id" in response.text
        except Exception as e:
            logger.debug(f"Device verification error: {e}")
            return False
    
    def generate(self) -> Optional[Device]:
        """Generate and register a new device with TikTok"""
        try:
            header_payload = self._generate_device_header()
            params = self._generate_params(header_payload)
            base_headers = self._generate_headers(header_payload)
            device_info = self._register_device(header_payload, params, base_headers)
            
            if not device_info:
                logger.warning("Failed to register device with TikTok")
                return None
            
            tokens = secrets.token_hex(16)
            cookies_dict = {"passport_csrf_token": tokens, "passport_csrf_token_default": tokens}
            
            if self._verify_device(device_info, header_payload, base_headers):
                sec_token = "A6RDV9Pib_ZYqYnv" + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(9))
                
                device = Device(
                    iid=device_info["install_id"],
                    did=device_info["device_id"],
                    device_type=params["device_type"],
                    device_brand=params["device_brand"],
                    os_version=params["os_version"],
                    cdid=params["cdid"],
                    openudid=params["openudid"],
                    version=random.choice(Config.VERSION_LIST),
                    sec_token=sec_token,
                    country=self.region.lower()
                )
                
                logger.info(f"Device generated: {device.device_brand} {device.device_type} | DID: {device.did[:16]}... | IID: {device.iid[:16]}...")
                return device
            else:
                logger.warning("Device verification failed")
                return None
        except Exception as e:
            logger.error(f"Device generation error: {e}")
            return None


class AccountCreator:
    def __init__(self, proxies: List[str], rambler_emails: List[Tuple[str, str]], use_dynamic_devices: bool = True):
        self.proxies = proxies
        self.rambler_emails = rambler_emails
        self.use_dynamic_devices = use_dynamic_devices
        self.lock = Lock()

    def generate_device(self, proxy: str = None) -> Optional[Device]:
        """Generate a device dynamically or return None if generation fails"""
        if self.use_dynamic_devices:
            region = random.choice(["US", "GB", "CA", "DE", "FR", "ES", "IT"])
            generator = DeviceGenerator(region=region, proxy=proxy)
            device = generator.generate()
            if device:
                return device
            else:
                logger.warning("Dynamic device generation failed, retrying...")
                return None
        else:
            logger.error("Static device loading not implemented in this version")
            return None

    @staticmethod
    def generate_credentials() -> str:
        password = f"{secrets.token_hex(random.randint(4, 6))}{random.randint(10000, 99999)}!"
        return password

    def create_account(self) -> None:
        try:
            with self.lock:
                if not self.rambler_emails:
                    logger.error("No more Rambler emails available!")
                    return
                
                email, email_password = self.rambler_emails.pop(0)
                remaining = len(self.rambler_emails)
                logger.info(f"Using email: {email} ({remaining} emails remaining)")
            
            proxy = random.choice(self.proxies)
            api = TikTokAPI(proxy)
            email_api = RamblerIMAPEmail(email, email_password)
            
            password = self.generate_credentials()

            device = self.generate_device(proxy)
            if not device:
                logger.error("Failed to generate device, returning email to pool")
                with self.lock:
                    self.rambler_emails.append((email, email_password))
                return
            
            domain = random.choice(Config.DOMAINS)

            response, params_str = api.send_code(domain, email, password, device)

            if 'success' in response.text:
                logger.info(f"Wait code {email}")

                code = email_api.get_verification_code(timeout=60, check_interval=5)

                if code:
                    logger.info(f"Code: {code}")

                    response = api.verify_code(domain, email, code, device)
                    data = response.json()

                    if "session_key" in response.text:
                        account_info = data["data"]
                        headers = response.headers

                        tt_token = headers["X-Tt-Token"]
                        multi_sids = headers["X-Tt-Multi-Sids"]
                        lanusk = headers.get("X-Bd-Lanusk", "")
                        sessionid = account_info["session_key"]
                        username = account_info["screen_name"]

                        account_line = f"{username}:{password}:{email}:{email_password}"

                        with lock:
                            open("accounts.txt", "a+").write(account_line + "\n")
                            logger.info(f"Account created - {account_line}")
                    else:
                        error_code = data.get("data", {}).get("error_code", "Unknown")
                        logger.warning(f"Account could not be opened. Error code: {error_code}")
                        with self.lock:
                            self.rambler_emails.append((email, email_password))
                else:
                    logger.warning("Not mail code")
                    with self.lock:
                        self.rambler_emails.append((email, email_password))
            else:
                logger.warning(f"Failed send code {email}")
                with self.lock:
                    self.rambler_emails.append((email, email_password))
        except Exception as e:
            logger.error(f"Error creating account: {e}")

    def run(self, threads: int):
        for _ in range(threads):
            Thread(target=self.worker).start()

    def worker(self):
        while True:
            self.create_account()

def load_data(filename: str) -> List[str]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return []

def load_rambler_emails(filename: str) -> List[Tuple[str, str]]:
    """
    Load Rambler email credentials from file
    Format: email:password (one per line)
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            emails = []
            for line in f.read().splitlines():
                if ':' in line:
                    email, password = line.split(':', 1)
                    emails.append((email.strip(), password.strip()))
            return emails
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return []

def main():
    system("title TikTok Creator ^| RUSOCIAL V3")

    proxies = load_data("data/proxy.txt")
    rambler_emails = load_rambler_emails("data/rambler_emails.txt")
    
    if not rambler_emails:
        logger.error("No Rambler emails found! Please add emails to data/rambler_emails.txt")
        logger.error("Format: email@rambler.ru:password (one per line)")
        return
    
    if not proxies:
        logger.warning("No proxies found in data/proxy.txt! Running without proxies (not recommended)")
        logger.warning("Format: ip:port:user:pass or ip:port")
    
    logger.info(f"Loaded {len(rambler_emails)} emails and {len(proxies)} proxies")
    logger.info("Using dynamic device generation (no devices.txt needed)")

    threads = int(input("Thread count: "))
    creator = AccountCreator(proxies, rambler_emails, use_dynamic_devices=True)
    creator.run(threads)

if __name__ == '__main__':
    main()

