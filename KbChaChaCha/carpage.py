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
    "_gid": "GA1.2.1067453222.1751522089",
    "_M_CS[T]": "1",
    "JSESSIONID": "6cf9yM0QccJgQEtCWm301hYn8bqA7hajvNpt4Cp1Nk8OTd9alAb84H4UjHDleAzI.cGNoYWFwbzFfZG9tYWluL0NBUjNBUF9zZXJ2ZXIyX2Nz",
    "_clck": "1uxyxt6%7C2%7Cfxb%7C0%7C1952",
    "_clsk": "103isa0%7C1751612830072%7C3%7C1%7Ck.clarity.ms%2Fcollect",
    "TR10062602448_t_uid": "58135152018410145.1751612844699",
    "TR10062602448_t_if": "15.0.0.0.null.null.null.0",
    "recent-visited-car": "27069369",
    "m_sid": "%7C1751612872939",
    "m_s_start": "1751612872939",
    "TR10062602448_t_sst": "58135612400001410.1751612894866",
    "wcs_bt": "unknown:1751612896",
    "_ga_BQD4DF40J4": "GS2.1.s1751612845$o7$g1$t1751612897$j8$l0$h1212231871",
    "_ga": "GA1.1.1660902199.1746506453",
    "page-no-action-count": "1",
}

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Referer": "https://www.kbchachacha.com/public/search/main.kbc",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    # 'Cookie': 'cha-cid=c6db4a30-8caf-4a3c-b188-d638a00a2d48; WMONID=D4THOVHkPFJ; _fwb=1PggEiMSm7GqDyOwNXR2C.1746506452712; _fcOM={"k":"bcab78b0f2c3357323903248196a3e344c26b3c","i":"219.240.196.205.8598","r":1746506452790}; _m_uid=08e53aad-88e0-32b5-a959-5110b02c3f92; _m_uid_type=A; _gcl_au=1.1.1587524517.1748851277; _m_uidt=C; cto_bundle=_dg1TF9sV3lCRFN3R0NuOUQ3ZUJFaFJhN1NqMnJwUFFtS09ZNjRoUzhKbWRNWGJaczg2QlU2R01LNHZ3RmpIeFV5Zk1xRiUyRlNoYWR0JTJCV1NyRkNqdE5QVFVBUG9DbmpSOUxyWDh1YXZiUFNFUWJoSENxZXFYOHVqOGs3Z0o4UzFhOGJ1bXY5NEh5NlZMNlNWVFM2ZEZjRE5MdGxkdDlSTlpQYnByJTJCR3JWSERVVEpvWkpqdiUyQm40QzgxUElTU3hCJTJCZzZBTyUyRjdpTlB4dVl3ZXRKeXFkSTdWb3pyT1B5aXM1RnA5MnhPWHBQdzlGSTNIN1FNRXFOUFpod3BBcyUyQkpzeGRMSVRJWkJYM0lkMHhuSEIlMkJmZzMzczRQc1JneXclM0QlM0Q; _ga_5F5EXL7QF0=GS2.1.s1748851449$o1$g1$t1748852293$j60$l0$h1944842216; _gid=GA1.2.1067453222.1751522089; _M_CS[T]=1; JSESSIONID=6cf9yM0QccJgQEtCWm301hYn8bqA7hajvNpt4Cp1Nk8OTd9alAb84H4UjHDleAzI.cGNoYWFwbzFfZG9tYWluL0NBUjNBUF9zZXJ2ZXIyX2Nz; _clck=1uxyxt6%7C2%7Cfxb%7C0%7C1952; _clsk=103isa0%7C1751612830072%7C3%7C1%7Ck.clarity.ms%2Fcollect; TR10062602448_t_uid=58135152018410145.1751612844699; TR10062602448_t_if=15.0.0.0.null.null.null.0; recent-visited-car=27069369; m_sid=%7C1751612872939; m_s_start=1751612872939; TR10062602448_t_sst=58135612400001410.1751612894866; wcs_bt=unknown:1751612896; _ga_BQD4DF40J4=GS2.1.s1751612845$o7$g1$t1751612897$j8$l0$h1212231871; _ga=GA1.1.1660902199.1746506453; page-no-action-count=1',
}

params = {
    "carSeq": "27069369",
}

response = requests.get(
    "https://www.kbchachacha.com/public/car/detail.kbc",
    params=params,
    cookies=cookies,
    headers=headers,
)
