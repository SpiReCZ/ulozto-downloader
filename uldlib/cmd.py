import argparse
import os
import signal
import sys
from os import path
from uldlib import downloader, captcha, __version__, __path__, const, utils
from uldlib.const import DEFAULT_CONN_TIMEOUT
from uldlib.torrunner import TorRunner


def run():
    parser = argparse.ArgumentParser(
        description='Download file from Uloz.to using multiple parallel downloads.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('url', metavar='URL', type=str,
                        help="URL from Uloz.to (tip: enter in 'quotes' because the URL contains ! sign)")
    parser.add_argument('--parts', metavar='N', type=int, default=10,
                        help='Number of parts that will be downloaded in parallel')
    parser.add_argument('--output', metavar='DIRECTORY',
                        type=str, default="./", help='Target directory')
    parser.add_argument('--auto-captcha', default=False, action="store_true",
                        help='Try to solve captchas automatically using TensorFlow')
    parser.add_argument('--conn-timeout', metavar='SEC', default=DEFAULT_CONN_TIMEOUT, type=int,
                        help='Set connection timeout for TOR sessions in seconds')
    parser.add_argument('--version', action='version', version=__version__)

    args = parser.parse_args()

    if args.auto_captcha:
        model_path = path.join(__path__[0], const.MODEL_FILENAME)
        captcha_solve_fnc = captcha.AutoReadCaptcha(
            model_path, const.MODEL_DOWNLOAD_URL)
    else:
        captcha_solve_fnc = captcha.tkinter_user_prompt

    tor = TorRunner(args.output)
    d = downloader.Downloader(tor, captcha_solve_fnc)

    # Register sigint handler
    def sigint_handler(sig, frame):
        d.terminate()
        print('Program terminated.')
        sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        d.download(args.url, args.parts, args.output, args.conn_timeout)
        # remove resume .udown file
        udown_file = args.output + const.DOWNPOSTFIX
        if os.path.exists(udown_file):
            print(f"Delete file: {udown_file}")
            os.remove(udown_file)
    finally:
        d.terminate()
