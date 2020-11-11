#!/usr/bin/env python
import csv
import time
import os
from random import randint
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
# If Cloudflare ever comes up...
USING_CLOUDSCRAPER = False
try:
    import cloudscraper
    requests.session = cloudscraper.create_scraper
    USING_CLOUDSCRAPER = True
except:
    pass


class GetYourDrugsTestedScraper:
    def __init__(self, human_readable=False):
        self.base_url = "https://getyourdrugstested.com/test-results-archive/"
        self.result_path_template = "page/{0}/"
        self.page_regex = re.compile(r"Page (\d*) of (\d*)")
        self.session = requests.session()
        if not USING_CLOUDSCRAPER:
            self.session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{0}.0.4103.97 Safari/537.36".format(randint(78,83))})

        self.session.headers.update(
            {
                "referrer": "https://getyourdrugstested.com/test-results-archive/",
                "accept": "*/*",
                "authority": "getyourdrugstested.com",
            }
        )
        self.field_cache = None
        self.human_readable = human_readable
        self.entries = 0

    @property
    def entry_count(self):
        if self.entries != 0:
            return self.entries
        pages_txt = BeautifulSoup(self.session.get(self.base_url).text, 'html.parser').find(
            "span", {"class": "page-number"}).get_text().split(" ")
        total_pages = int(pages_txt[-1])
        total_count = (total_pages - 1) * 50
        last_page_output = self.session.get(self.base_url + self.result_path_template.format(total_pages)).text
        total_count += len(BeautifulSoup(last_page_output,'html.parser').find('table').findAll("tr"))
        self.entries = total_count
        return self.entries
        
    def get_page(self, page_number=1):
        return self.__process_rows__(self.session.get(self.base_url + self.result_path_template.format(page_number), allow_redirects=True).text)

    def __process_rows__(self, table):
        soup = BeautifulSoup(table, 'html.parser')
        return [[':'.join(y.get_text().split(":")[1:]).strip() if ':' in y.get_text() else y.get_text() for y in x.findAll("td")] for x in soup.find('table').findAll("tr") if x != None and x.find('th') == None]

    # If the table structure changes, let's make sure we're getting our fields correct.
    @property
    def fields(self):
        if self.field_cache:
            return self.field_cache
        html = self.session.get(self.base_url).text
        soup = BeautifulSoup(html, 'html.parser')
        fields = [x.get_text().strip() for x in soup.find('table').find("thead").findAll("th")]
        self.field_cache = fields
        return self.field_cache


if __name__ == "__main__":
    scraper = GetYourDrugsTestedScraper()
    fields = scraper.fields
    cur_date = str((datetime.utcnow() - timedelta(hours=8)).strftime("%Y-%m-%d"))
    print(scraper.entry_count)
    artifact_dir = os.path.abspath(os.path.join(os.getcwd(), "artifacts"))
    if not os.path.exists(artifact_dir):
        os.makedirs(artifact_dir)

    with open(os.path.join(artifact_dir, "GYDT Full Data - " + cur_date + ".csv"), "w") as csvf:
        csv_file = csv.writer(csvf, quoting=csv.QUOTE_ALL)
        csv_file.writerow(fields)

        test_results = 0
        for x in range(1, int(scraper.entry_count / 50) + 1):
            for attempt_number in range(1, 5):
                try:
                    print("Retrieving page {0}. Test result total: {1}".format(x, test_results))
                    res = scraper.get_page(x)
                    csv_file.writerows(res)                    
                    test_results += len(res)
                    break
                except Exception as e:
                    print("Need to delay a moment...", e)
                    time.sleep(10 * attempt_number)
                    pass
