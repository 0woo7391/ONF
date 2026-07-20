import os

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
os.environ.setdefault("OPENCV_VIDEOIO_PRIORITY_OBSENSOR", "0")

from onf_v2.ui.main_window import run


if __name__ == "__main__":
    raise SystemExit(run())
