""" run the comparisons using asyncio """

import asyncio
import asks
import trio
import settings
from time import sleep
from google.cloud import storage
from glob import glob
from datetime import datetime
from gcloud.aio.storage import Storage
from aiohttp import ClientSession as Session


async def parent(counter, inp):
    print("running parent")
    async with Session() as session:
        storage = Storage(session=session)
        bucket = storage.get_bucket(settings.bucket_name)
        blobs = await bucket.list_blobs()
        await asyncio.gather(*[storageio(x, inp, bucket, session) for x in blobs])
    return


async def storageio(blob, inp, bucket, session):
    status = 0
    max_out = 0
    try:
        blob_object = await bucket.get_blob(blob, session=session)
        raw_data = await blob_object.download()
        while (status != 200) and (max_out <= 10):
            async with session.post(
                settings.cloud_function, json={"d": inp, "e": str(raw_data)}
            ) as resp:
                print(resp.status, blob_object.name)
                status = resp.status
                if status == 503:
                    # truncate the data if there is a memory error
                    raw_data = raw_data[:100000]
                max_out += 1
                comp[blob_object.name[10:19]] = await resp.text()
    except asyncio.TimeoutError:
        print("timeout")
        pass
    return


def test_response(resp):
    try:
        return float(resp)  # will evaluate as false if float == 0.0
    except ValueError:
        return False


async def tabulate(data):
    to_sort = [(k, v) for k, v in comp.items() if test_response(v)]
    print("Journals checked:" + str(len(to_sort)))
    top = sorted(to_sort, key=lambda x: x[1], reverse=True)[:5]

    async with trio.open_nursery() as nursery:
        for idx, item in enumerate(top):
            nursery.start_soon(titles, idx, item)
    return


async def titles(idx, item):
    journal_data = await asks.get(
        "https://doaj.org/api/v1/search/journals/issn%3A" + item[0]
    )
    journal_json = journal_data.json()
    try:
        title = journal_json["results"][0]["bibjson"]["title"]
    except:
        title = "[title not found... look up by ISSN]"
    rank = idx + 1
    issn = item[0]
    score = item[1]
    scores[rank] = (issn, title, score)
    return


if __name__ == "__main__":
    comp = {}
    scores = {}
    inp = input("Abstract: ")
    counter = 0
    t0 = datetime.now()

    asyncio.run(parent(counter, inp))
    print("Counter: " + str(counter))

    trio.run(tabulate, comp)
    print(scores)
    t1 = datetime.now()
    print(t1 - t0)
