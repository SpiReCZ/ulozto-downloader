#!/usr/bin/env python3

import asyncio
import os
import signal
import urllib.parse
from multiprocessing import Queue, Process
from os import path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTasks
from starlette.responses import JSONResponse

from uldlib import captcha, const
from uldlib.downloader import Downloader
from uldlib.segfile import SegFileReader

app = FastAPI()

data_folder = os.getenv('DATA_FOLDER', '')
download_path = os.getenv('DOWNLOAD_FOLDER', '')
default_parts = os.getenv('PARTS', 10)

model_path = path.join(data_folder, "model.tflite")
captcha_solve_fnc = captcha.AutoReadCaptcha(
    model_path, const.MODEL_DOWNLOAD_URL)

downloader: Downloader = None
process: Process = None
queue: Queue = None


async def generate_stream(filename: str, parts: int):
    for seg_idx in range(parts):
        reader = SegFileReader(filename, parts, seg_idx)
        async for data in reader.read():
            yield data


def downloader_worker(url: str, parts: int, target_dir: str):
    signal.signal(signal.SIGINT, sigint_sub_handler)
    downloader.download(url, parts, target_dir)


def cleanup():
    global downloader, process, queue
    if process is not None:
        process.join()
        process = None
    if queue is not None:
        queue.close()
        queue = None
    if downloader is not None:
        downloader.terminate()
        downloader = None


def initiate(url: str, parts: int):
    global downloader, process, queue

    queue = Queue()
    downloader = Downloader(captcha_solve_fnc, False, queue)
    process = Process(target=downloader_worker,
                      args=(url, parts, download_path))
    process.start()


@app.get("/download", responses={
    200: {"content": {const.MEDIA_TYPE_STREAM: {}}, },
    429: {"content": {const.MEDIA_TYPE_JSON: {}}, }
})
async def download_endpoint(background_tasks: BackgroundTasks, url: str, parts: Optional[int] = default_parts):
    global downloader, process, queue

    # TODO: What happens when the same url is called twice and parts number changes?
    if downloader is not None:
        return JSONResponse(
            content=[{"url": f"{url}",
                      "message": "Downloader is busy.. Free download is limited to single download."}],
            status_code=429
        )

    if "#!" in url:
        url = url.split("#!")[0]
    initiate(url, parts)

    background_tasks.add_task(cleanup)
    file_data: tuple = await asyncio.get_event_loop().run_in_executor(None, queue.get, True, 60)

    filename = file_data[0]
    filename_encoded = urllib.parse.quote_plus(filename)
    size = file_data[1]

    return StreamingResponse(
        generate_stream(filename, parts),
        headers={
            "Content-Length": str(size),
            "Content-Disposition": f"attachment; filename=\"{filename_encoded}\"",
        }, media_type=const.MEDIA_TYPE_STREAM)


def sigint_sub_handler(sig, frame):
    downloader.terminate()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
