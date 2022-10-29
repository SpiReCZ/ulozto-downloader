import sys
import threading
from typing import Dict, List

import colors

from uldlib import utils
from uldlib.frontend import Frontend, DownloadInfo
from uldlib.part import DownloadPart
from uldlib.utils import LogLevel


class WebAppFrontend(Frontend):

    def __init__(self, supports_prompt=False):
        super().__init__(supports_prompt)

    def captcha_log(self, msg: str, level: LogLevel = LogLevel.INFO):
        sys.stdout.write(colors.blue("[Link solve]\t") + utils.color(msg, level) + "\033[K\r\n")

    def captcha_stats(self, stats: Dict[str, int]):
        pass

    def main_log(self, msg: str, level: LogLevel = LogLevel.INFO):
        print(utils.color(msg, level))

    def tor_log(self, msg: str, level: LogLevel = LogLevel.INFO, progress: bool = False):
        print(utils.color(msg, level))

    def prompt(self, msg: str, level: LogLevel = LogLevel.INFO) -> str:
        if not self.supports_prompt:
            raise Exception('Prompt not supported')
        return ""

    def run(self, info: DownloadInfo, parts: List[DownloadPart], stop_event: threading.Event, terminate_func):
        pass
