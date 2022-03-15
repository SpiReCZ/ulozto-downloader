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

from uldlib import captcha, const, utils
from uldlib.downloader import Downloader
from uldlib.segfile import SegFileReader
from uldlib.torrunner import TorRunner

app = FastAPI()

temp_path: str = os.getenv('TEMP_FOLDER', '')
data_folder: str = os.getenv('DATA_FOLDER', '')
download_path: str = os.getenv('DOWNLOAD_FOLDER', '')
default_parts: int = int(os.getenv('PARTS', 10))
auto_delete_downloads: bool = os.getenv('AUTO_DELETE_DOWNLOADS', '1').strip().lower() in ['true', '1', 't', 'y', 'yes']

model_path = path.join(data_folder, const.MODEL_FILENAME)
captcha_solve_fnc = captcha.AutoReadCaptcha(
    model_path, const.MODEL_DOWNLOAD_URL)

downloader: Downloader = None
process: Process = None
queue: Queue = None
tor: TorRunner = None


async def generate_stream(file_path: str, parts: int):
    for seg_idx in range(parts):
        reader = SegFileReader(file_path, parts, seg_idx)
        async for data in reader.read():
            yield data


def downloader_worker(url: str, parts: int, target_dir: str):
    signal.signal(signal.SIGINT, sigint_sub_handler)
    downloader.download(url, parts, target_dir)


def cleanup(file_path: str = None):
    global downloader, process, queue, tor
    if process is not None:
        process.join()
        process = None
    if queue is not None:
        queue.close()
        queue = None
    if tor is not None:
        tor = None
    if downloader is not None:
        downloader.terminate()
        downloader = None
    if auto_delete_downloads and file_path is not None:
        os.remove(file_path + const.DOWNPOSTFIX)
        os.remove(file_path + const.CACHEPOSTFIX)
        os.remove(file_path)


def initiate(url: str, parts: int):
    global downloader, process, queue, tor

    tor = TorRunner(download_path)
    queue = Queue()
    downloader = Downloader(tor, captcha_solve_fnc, False, queue)
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

    url = utils.strip_tracking_info(url)
    initiate(url, parts)

    file_data: tuple = await asyncio.get_event_loop().run_in_executor(None, queue.get, True, 60)

    file_path = file_data[0]
    filename = file_data[1]
    filename_encoded = urllib.parse.quote_plus(filename)
    size = file_data[2]

    background_tasks.add_task(cleanup, file_path)

    return StreamingResponse(
        generate_stream(file_path, parts),
        headers={
            "Content-Length": str(size),
            "Content-Disposition": f"attachment; filename=\"{filename_encoded}\"",
        }, media_type=const.MEDIA_TYPE_STREAM)


def sigint_sub_handler(sig, frame):
    downloader.terminate()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
