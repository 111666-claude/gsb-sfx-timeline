"""命令行入口：跑音效时间线样例。"""

import argparse

from .timeline import play, sample


def build_parser():
    parser = argparse.ArgumentParser(prog="sfx-timeline", description="音效事件时间线")
    parser.add_argument("--script", default="sample", help="sample")
    return parser


def main(argv=None):
    build_parser().parse_args(argv)
    played, cut = play(sample())
    print("played=%d cut=%d" % (len(played), cut))
    for event in played:
        print("event name=%s at=%d volume=%d priority=%d"
              % (event.name, event.at, event.volume, event.priority))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
