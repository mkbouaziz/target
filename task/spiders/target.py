# -*- coding: utf-8 -*-

import scrapy
import requests
import re
import json
from pprint import pprint

from task.items import TaskItem

class TargetSpider(scrapy.Spider):
    name = "target"

    def start_requests(self):
        urls = [
            "https://www.target.com/p/apple-iphone-13-pro-max/-/A-84616123?preselect=84240109#lnk=sametab",
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        task_item = TaskItem()
        # Get API Key
        for i in response.css('script::text').getall():
            if i.startswith('window.__PRELOADED_STATE__= '):
                text = re.sub(r'^window\.__PRELOADED_STATE__= ','',i)
                text = re.sub(r'undefined','null',text)
                text = re.sub(r'new Set\(\[\]\)','[]',text)
                temp = json.loads(text)
                api_key = temp['config']['firefly']['apiKey']
                break
        # Get ids
        sku,tcin = '',''
        res = re.search(r'-(\d+)\?preselect=(\d+)',response.url)
        if res:
            sku,tcin = res.groups()
        # Use 1st API
        url=f"https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1?key={api_key}&tcin={sku}&pricing_store_id=3991"
        res = requests.get(url)
        result = res.json()
        # Title
        task_item['title'] = result['data']['product']['item']['product_description']['title']
        # Highlights
        task_item['highlights'] = []
        if result['data']['product']['item']['product_description']['soft_bullets']['title']=='highlights':
            task_item['highlights'] = result['data']['product']['item']['product_description']['soft_bullets']['bullets']
        # Images
        task_item['images'] = []
        for i in result['data']['product']['variation_hierarchy']:
            itemtop = {i['name'].lower():i['value']}
            for j in i['variation_hierarchy']:
                item=itemtop
                item.update({j['name'].lower():j['value'],'url':j['primary_image_url']})
                task_item['images'].append(item)
        # Prices
        task_item['prices']=[]
        for i in result['data']['product']['children']:
            if i['tcin']==tcin:
                # Description
                task_item['description'] = i['item']['product_description']['downstream_description']
                for j in i['connected_commerce']['products']:
                    if j['tcin']==tcin:
                        for k in j['locations'][0]['carriers']:
                            task_item['prices'].append({'seller':k['name'],'price':k['price']['current_retail']})
                        break
                break
        # Specifications
        task_item['specifications']=[re.sub('(<B>|</B>)','',i) for i in result['data']['product']['item']['product_description']['bullet_descriptions']]
        # Use 2nd API
        url=f"https://r2d2.target.com/ggc/Q&A/v1/question-answer?type=product&questionedId={sku}&sortBy=MOST_ANSWERS&key=c6b68aaef0eac4df4931aae70500b7056531cb37"
        res = requests.get(url)
        result = res.json()
        # Questions
        task_item['questions'] = [i['text'] for i in result['results']]
        pprint(task_item)