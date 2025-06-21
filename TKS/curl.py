import requests

cookies = {
    "_gid": "GA1.2.1217157838.1750464978",
    "_ym_uid": "1747226371917027955",
    "_ym_d": "1750464979",
    "_ym_isad": "1",
    "tmr_lvid": "028e5af71c6a0442a357ab8b5123dd94",
    "tmr_lvidTS": "1747226370675",
    "domain_sid": "XjKf1qCx2XfHUawYJjZsL%3A1750464996505",
    "csrftoken": "CdY4pRKs17d1nVuaX7X7cMitdslHdVhZ",
    "_ym_visorc": "w",
    "_ga_ZX8WYPEF25": "GS2.1.s1750472576$o2$g1$t1750473349$j60$l0$h0",
    "_ga": "GA1.2.939613630.1750464978",
    "_gat_gtag_UA_316975_1": "1",
    "tmr_detect": "0%7C1750473352862",
}

headers = {
    "accept": "*/*",
    "accept-language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
    "priority": "u=1, i",
    "referer": "https://www.tks.ru/auto/calc/",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
    # 'cookie': '_gid=GA1.2.1217157838.1750464978; _ym_uid=1747226371917027955; _ym_d=1750464979; _ym_isad=1; tmr_lvid=028e5af71c6a0442a357ab8b5123dd94; tmr_lvidTS=1747226370675; domain_sid=XjKf1qCx2XfHUawYJjZsL%3A1750464996505; csrftoken=CdY4pRKs17d1nVuaX7X7cMitdslHdVhZ; _ym_visorc=w; _ga_ZX8WYPEF25=GS2.1.s1750472576$o2$g1$t1750473349$j60$l0$h0; _ga=GA1.2.939613630.1750464978; _gat_gtag_UA_316975_1=1; tmr_detect=0%7C1750473352862',
}

response = requests.get(
    "https://www.tks.ru/auto/calc/?cost=1000000&captcha=03AFcWeA5gh0EEpRBzYZ4SavT0IGR98ay3Ka5wHd75U4ibK6vcYhchnt3NJTDXFHQ_4j5ER3MrhVN6xp32iXVJA5SYXzCotP46ZHpffvz0hX5J3mdClYYXeMDCemYMZPbIVgw8oTovPbMfiur0G7g6m0foPoI3UJNlk7b1nYvGyAif_3CHfchZDefv5--zj717xJ0CrhkM9kLlKz8yl4A3nEB5CSxe5vYlf3uQurvvtIkBJKIJQkRpM0aXTka2tNxlrgD8fJOvkFafzn7W0gArTA1bT10L100ATgUQgGNkZuyQisTjkXpAcGP4GrkHbuGx9tSQEMFLMoAI6pBJ8XiFqAW7SdyG3zNUG9jHdGYxHEC4wtP8aJ3Cozty8Pc6Y0pDyQxBZ48Z8BrhngOp3Iqt8F_QLeh1PF0BvgKCQEBBscwWhkXJdwSpBSa2fYhHVNCJRDnGFgI9Bv8HuqPtR-JPJhkKY0jrKlPAJZdQubOJgFCSW5rGeLHGK3osBwDVbTiELsXZn4OO8AngWTOC6VpK9JvI2fSeQQQHMiwXIhq8FS7HIVCGoWdEjllCLIGC1Oj34syJ5ZmxPgMYhD724f2zI4msAmk5GNdFkv5zMZm-hwrDAP0LQ2GFGZKZFawHF2k591Axsed0QlPuXAPz6wK6y8mOWA0aJ0f2Bcq_jibM0l8hLnvIuMGBICgxhu9vTCDV583Rp4deKpqwLid15Hwe-FKRHkS6shdxBhvIDbViD9YsNKmhbK4bsqIt-vPPzPPztAsCUz9jKnkP2pNHF5_EaN9JkBfKhG84sRa4YACiGorMGvs67L9lZ4ZXDLI-OYSgfyJtbk1frb9HXbGg9whGlo3MzuRPTODHzi3tSfRDKYOrmRYZHRr8qt10BDIpcn9kmFXHOPVUkon1CVqFKvZHXNpA0hFRRE37I3U5pD0vb3kIdYedmjFvYqwnLuDgKwtE-QrlKzeqARkizHn10LIG0P_HVRj9ouAS0Q&volume=355&currency=410&power=1&power_edizm=ls&country=noru&engine_type=petrol&age=3&face=jur&ts_type=06_8711&mass=&chassis=shs&forwarder=false&caravan=false&offroad=false&buscap=lt120&mdvs_gt_m30ed=true&sequential=false&boat_sea=&sh2017=&bus_municipal_cb=&mode=ajax&t=1;",
    cookies=cookies,
    headers=headers,
)
