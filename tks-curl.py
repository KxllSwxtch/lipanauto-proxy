import requests

headers = {
    "sec-ch-ua-platform": '"macOS"',
    "Referer": "https://www.tks.ru/auto/calc/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
}

response = requests.get(
    "https://www.tks.ru/auto/calc/?cost=3500000&captcha=03AFcWeA4BmxauDri-FlXHY6cW1luM4gsW2my7uXt6k_qo4W59HiuSc2fKOTcAfKOxvSZEeLWe9VuuIvg2dY7qOlUkJ0ALI8xLEEQdH6y_vJyi9lP-3CdY4TSH_4q_GFztT4yyc7Skebh5Kj8l_osYqNB4HSx3mGPIGozdKin8EMYo25PHlWnkOsTPw6xVDtFwokk-aC6Hk-Yn2qhqc_OeiFpUR_rG0HT2yKLkArZQ4Qf33doCve8waTrsHgi9n89Ybksf4eHCMTwZh_iblrr-JJLulZQSBG9vjLXLRkNlpBkxIfPEw92lC4iheEVK7N21_s7z5v0ONFz-vClvSmTe8-VRPMCu10fnidZn7l6Q7pxBHtX0wWI6G92bDrbw4XAE35KMoxpHHZBAksU9UmYvfjLg7R8I7YlRdIaew3pVgArvNhWK-pCyA4NDf4zZlANzwlYP0Al5nAjwY6U4b1dpD3QAeG8iC69118tO4kn5AEr_ma0ThMJ3Yil10pBQrowYDyl-BEzaLh6wOdZ1qmFk3jBuyUexMNM5SJDFieYUQwD6kwQBqKagStJi3JhP8GjTx9n5Xvc1_mrlQlu5oQsh9QxpglQ3OndeuFfRGRQ_SmUE5as__zguXwUMsvnn0AADlAn1JOXTpWxmw_OqgqhCfusgWJnDIKxACvMwK8vJP_DHolIy-bPkE6X-ZF_pNcUlWhbiB5LnTy-2aF_6_AIzCEkJsU7f-9SeQPweTvwjiJJDYJYmICQdJip51XkRDHC3va68-w8F8buIfzEqk4Vymx7ALQWjAfy5aYl3I34zFqMq18_7lBZp3mNly23rcKj9tw1d0Uj1PIhGq_0rxifik-tUGXD44-Zyj7uU0BH1Ccots_6MkAK29M7snyor__H0WqvcA8SHGs7Gs7Dx5raizlrezs-vpHGzRleBtpRp7OKGHyA7LN91_8Su-K7JB-4p4hvL6sPZZ6tA&volume=125&currency=410&power=1&power_edizm=ls&country=noru&engine_type=petrol&age=3&face=jur&ts_type=06_8711&mass=&chassis=shs&forwarder=false&caravan=false&offroad=false&buscap=lt120&mdvs_gt_m30ed=true&sequential=false&boat_sea=&sh2017=&bus_municipal_cb=&mode=ajax&t=1;",
    headers=headers,
)
