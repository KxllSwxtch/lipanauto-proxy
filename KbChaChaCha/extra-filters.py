import requests

cookies = {
    "cha-cid": "c6db4a30-8caf-4a3c-b188-d638a00a2d48",
    "WMONID": "D4THOVHkPFJ",
    "_fwb": "1PggEiMSm7GqDyOwNXR2C.1746506452712",
    "_fcOM": '{"k":"bcab78b0f2c3357323903248196a3e344c26b3c","i":"219.240.196.205.8598","r":1746506452790}',
    "_m_uid": "08e53aad-88e0-32b5-a959-5110b02c3f92",
    "_m_uid_type": "A",
    "_gcl_au": "1.1.1587524517.1748851277",
    "_m_uidt": "C",
    "cto_bundle": "_dg1TF9sV3lCRFN3R0NuOUQ3ZUJFaFJhN1NqMnJwUFFtS09ZNjRoUzhKbWRNWGJaczg2QlU2R01LNHZ3RmpIeFV5Zk1xRiUyRlNoYWR0JTJCV1NyRkNqdE5QVFVBUG9DbmpSOUxyWDh1YXZiUFNFUWJoSENxZXFYOHVqOGs3Z0o4UzFhOGJ1bXY5NEh5NlZMNlNWVFM2ZEZjRE5MdGxkdDlSTlpQYnByJTJCR3JWSERVVEpvWkpqdiUyQm40QzgxUElTU3hCJTJCZzZBTyUyRjdpTlB4dVl3ZXRKeXFkSTdWb3pyT1B5aXM1RnA5MnhPWHBQdzlGSTNIN1FNRXFOUFpod3BBcyUyQkpzeGRMSVRJWkJYM0lkMHhuSEIlMkJmZzMzczRQc1JneXclM0QlM0Q",
    "_ga_5F5EXL7QF0": "GS2.1.s1748851449$o1$g1$t1748852293$j60$l0$h1944842216",
    "JSESSIONID": "XwuA8Y3YeKcHBfoX0hkpwHl3uWsaSRUOzw6lX15tzm3aRAYClaYZFkzu34wkU9S1.cGNoYWFwbzFfZG9tYWluL0NBUjNBUF9zZXJ2ZXIxX2Nz",
    "_gid": "GA1.2.1067453222.1751522089",
    "_clck": "1uxyxt6%7C2%7Cfxa%7C0%7C1952",
    "m_sid": "%7C1751522091152",
    "m_s_start": "1751522091152",
    "_M_CS[T]": "1",
    "TR10062602448_t_uid": "58135152018108165.1751522156093",
    "TR10062602448_t_if": "15.0.0.0.null.null.null.0",
    "TR10062602448_t_sst": "58135520600001108.1751523277798",
    "wcs_bt": "unknown:1751523278",
    "_ga": "GA1.1.1660902199.1746506453",
    "_clsk": "x6u627%7C1751524238040%7C6%7C1%7Cs.clarity.ms%2Fcollect",
    "_ga_BQD4DF40J4": "GS2.1.s1751522090$o5$g1$t1751524615$j45$l0$h132702711",
}

headers = {
    "Accept": "*/*",
    "Accept-Language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
    "Connection": "keep-alive",
    "Referer": "https://www.kbchachacha.com/public/search/main.kbc",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    # 'Cookie': 'cha-cid=c6db4a30-8caf-4a3c-b188-d638a00a2d48; WMONID=D4THOVHkPFJ; _fwb=1PggEiMSm7GqDyOwNXR2C.1746506452712; _fcOM={"k":"bcab78b0f2c3357323903248196a3e344c26b3c","i":"219.240.196.205.8598","r":1746506452790}; _m_uid=08e53aad-88e0-32b5-a959-5110b02c3f92; _m_uid_type=A; _gcl_au=1.1.1587524517.1748851277; _m_uidt=C; cto_bundle=_dg1TF9sV3lCRFN3R0NuOUQ3ZUJFaFJhN1NqMnJwUFFtS09ZNjRoUzhKbWRNWGJaczg2QlU2R01LNHZ3RmpIeFV5Zk1xRiUyRlNoYWR0JTJCV1NyRkNqdE5QVFVBUG9DbmpSOUxyWDh1YXZiUFNFUWJoSENxZXFYOHVqOGs3Z0o4UzFhOGJ1bXY5NEh5NlZMNlNWVFM2ZEZjRE5MdGxkdDlSTlpQYnByJTJCR3JWSERVVEpvWkpqdiUyQm40QzgxUElTU3hCJTJCZzZBTyUyRjdpTlB4dVl3ZXRKeXFkSTdWb3pyT1B5aXM1RnA5MnhPWHBQdzlGSTNIN1FNRXFOUFpod3BBcyUyQkpzeGRMSVRJWkJYM0lkMHhuSEIlMkJmZzMzczRQc1JneXclM0QlM0Q; _ga_5F5EXL7QF0=GS2.1.s1748851449$o1$g1$t1748852293$j60$l0$h1944842216; JSESSIONID=XwuA8Y3YeKcHBfoX0hkpwHl3uWsaSRUOzw6lX15tzm3aRAYClaYZFkzu34wkU9S1.cGNoYWFwbzFfZG9tYWluL0NBUjNBUF9zZXJ2ZXIxX2Nz; _gid=GA1.2.1067453222.1751522089; _clck=1uxyxt6%7C2%7Cfxa%7C0%7C1952; m_sid=%7C1751522091152; m_s_start=1751522091152; _M_CS[T]=1; TR10062602448_t_uid=58135152018108165.1751522156093; TR10062602448_t_if=15.0.0.0.null.null.null.0; TR10062602448_t_sst=58135520600001108.1751523277798; wcs_bt=unknown:1751523278; _ga=GA1.1.1660902199.1746506453; _clsk=x6u627%7C1751524238040%7C6%7C1%7Cs.clarity.ms%2Fcollect; _ga_BQD4DF40J4=GS2.1.s1751522090$o5$g1$t1751524615$j45$l0$h132702711',
}

response = requests.get(
    "https://www.kbchachacha.com/public/search/list.empty?page=1&sort=-orderDate&makerCode=101&classCode=1108&carCode=3330&modelCode=26892&modelGradeCode=26892%7C002,26892%7C003&regiDay=2023,2025&km=0,200000&sellAmt=0,99999&gas=004001",
    cookies=cookies,
    headers=headers,
)
