""" run the comparisons using trio (async) """

import json
import asks
import multio
import trio
import glob
import requests
import base64
import settings
from datetime import datetime

comp = {}
inp = input("Abstract: ")
counter = 0
t0 = datetime.now()


async def parent(counter, inp):
    print("running parent")
    async with trio.open_nursery() as nursery:
        for item in glob.glob("docs-small-file-size/*")[:60]:
            counter += 1
            nursery.start_soon(fileio, item, inp)


async def fileio(item, inp):
    async with await trio.open_file(item, encoding="latin-1", mode="r") as i:
        print("open context")
        data = await i.read()
        print("data read")
        data = json.dumps({"d": inp, "e": data})
    resp = await asks.put(
        settings.cloud_function, 
        data=data,
        )
    print("request sent")
    comp[item[21:]] = resp.text 
    print(resp.text)
    return


multio.init("trio")
trio.run(parent, counter, inp)

print("sorting")
to_sort = [(k, v) for k, v in comp.items() if 'Error' not in v]
top = sorted(to_sort, key=lambda x: x[1], reverse=True)[:5]
print(top)

print("get journal info from API")
for item in top:
    journal_data = requests.get(
        "https://doaj.org/api/v1/search/journals/issn%3A" + item[0]
    )
    journal_json = journal_data.json()
    try:
        title = journal_json["results"][0]["bibjson"]["title"]
    except:
        title = " "
    issn = item[0]
    score = item[1]
    print(issn, title)

t1 = datetime.now()
print(t1 - t0)
