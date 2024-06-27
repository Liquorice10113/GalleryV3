import os, json, time, shutil
import config
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except:
    print("Heif not supported.\nTry python3 -m pip install pillow-heif.")
from hashlib import md5
import subprocess
import natsort
from threading import Lock
import random

vol = 1

file_list_cache = dict()
file_list_scan_time = dict()
file_list_sorted_cache = dict()
param_cache = dict()

star_list = set()
star_added_date = dict()
star_list_sort_cache = {"name": [], "date": [], "size": [], "rand": []}

filters = dict()

last_scan_time = -1

ls_lock = Lock()


def dump_cache(star_only=False):
    global file_list_cache, file_list_scan_time, file_list_sorted_cache, param_cache, star_list, star_added_date
    if not star_only:
        data = {
            "file_list_cache": file_list_cache,
            "file_list_scan_time": file_list_scan_time,
            "file_list_sorted_cache": file_list_sorted_cache,
            "param_cache": param_cache,
        }
        json.dump(data, open("cache.json", "w"))
    data = {"star_list": list(star_list), "star_added_date": star_added_date}
    json.dump(data, open("stars.json", "w"))


def load_cache():
    global file_list_cache, file_list_scan_time, file_list_sorted_cache, param_cache, star_list, star_added_date

    if os.path.exists("cache.json"):
        data = json.load(open("cache.json", "r"))
        file_list_cache = data["file_list_cache"]
        file_list_scan_time = data["file_list_scan_time"]
        file_list_sorted_cache = data["file_list_sorted_cache"]
        param_cache = data["param_cache"]
    if os.path.exists("stars.json"):
        data = json.load(open("stars.json", "r"))
        star_list = set(data["star_list"])
        star_added_date = data["star_added_date"]


file_types = [
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "bmp",
    "mp4",
    "mkv",
    "webm",
    "avi",
    "mpeg",
    "mov",
    "m4v",
    "mview"
]
image_types = ["jpg", "jpeg", "png", "gif", "webp", "bmp"]


def is_media(s):
    return s.split(".")[-1].lower() in file_types


def is_img(s):
    return s.split(".")[-1].lower() in image_types


def get_hash(s):
    return md5(s.encode("utf-8")).hexdigest()


def get_param(path):
    if path in param_cache:
        param = param_cache[path]
    else:
        param = {
            "fit": -1,
            "sort": config.sort_type,
            "r": config.sort_reverse,
            "index": 0,
            "star": 0,
            "scroll": 0,
        }
    # print("Get", path)
    # print(param)
    return param


def listdir(p, sort_type="name", reverse=config.sort_reverse):
    global ls_lock, last_scan_time
    try:
        ls_lock.acquire()
        if not p in file_list_cache or (
            p in file_list_cache and os.path.getmtime(p) - file_list_scan_time[p] > 60
        ):
            if p in file_list_cache and file_list_scan_time[p] < os.path.getmtime(p):
                print("file_list_scan_time[p] < os.path.getmtime(p)")
            files = os.listdir(p)
            if ".ignore" in files:
                files = []
            files = [
                i
                for i in files
                if (
                    os.path.isdir(os.path.join(p, i))
                    or i.split(".")[-1].lower() in file_types
                )
                and not i.startswith(".")
                and not i.startswith("$")
                and not i.startswith("found.")
                and not i.startswith("System Volume")
            ]
            file_list_cache[p] = files
            file_list_scan_time[p] = os.path.getmtime(p)
            for t_sort_type in ["name", "date", "size", "rand"]:
                if (
                    p in file_list_sorted_cache
                    and t_sort_type in file_list_sorted_cache[p]
                ):
                    del file_list_sorted_cache[p][t_sort_type]
        if not (p in file_list_sorted_cache and sort_type in file_list_sorted_cache[p]):
            files = file_list_cache[p]
            if not p in file_list_sorted_cache:
                file_list_sorted_cache[p] = dict()
            if sort_type == "name":
                file_list_sorted_cache[p][sort_type] = natsort.natsorted(files)
            elif sort_type == "date":
                file_list_sorted_cache[p][sort_type] = sorted(
                    files, key=lambda x: os.path.getmtime(os.path.join(p, x))
                )
            elif sort_type == "size":
                file_list_sorted_cache[p][sort_type] = sorted(
                    files, key=lambda x: os.path.getsize(os.path.join(p, x))
                )
            elif sort_type == "rand":
                file_list_sorted_cache[p][sort_type] = list(files)
                random.shuffle(file_list_sorted_cache[p][sort_type])
            else:
                print("What is " + sort_type + "?")
                raise
            if time.time() - last_scan_time > 120:
                dump_cache()
                last_scan_time = time.time()
        ls_lock.release()
        if p in filters:
            res = [
                i
                for i in file_list_sorted_cache[p][sort_type]
                if filters[p].lower() in i.lower()
            ]
        else:
            res = file_list_sorted_cache[p][sort_type]
        if reverse:
            return res[::-1]
        else:
            return res
    except Exception as e:
        ls_lock.release()
        print(e)


def thumbnails(p, size=0):
    # print(size, "x", size)
    if size == 0:
        size = config.thumbnail_size
    hash = get_hash(p)
    cache_folder = os.path.expanduser(config.cache_folder)
    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)
    if os.path.exists(os.path.join(cache_folder, "{}_{}.jpg".format(hash, size))):
        print("Serving", p, "from cache.")
        return os.path.join(cache_folder, "{}_{}.jpg".format(hash, size))
    if os.path.exists(os.path.join(cache_folder, "{}_v.jpg".format(hash))):
        print("Serving", p, "from cache.")
        return os.path.join(cache_folder, "{}_v.jpg".format(hash))
    if is_img(p):
        print("Creating thumbnail", p)
        image = Image.open(p)
        image = image.convert("RGB")
        scale = max(image.size) / size
        new_size = (int(image.size[0] / scale), int(image.size[1] / scale))
        image.thumbnail(new_size)
        image.save(os.path.join(cache_folder, "{}_{}.jpg".format(hash, size)))
        return os.path.join(cache_folder, "{}_{}.jpg".format(hash, size))
    else:
        img_output_path = os.path.join(cache_folder, "{}_v.jpg".format(hash))
        cmd = 'ffmpeg -i "{}" -ss 00:00:05.000 -vframes 1 -vf scale=640:-1 "{}"'.format(
            p, img_output_path
        )
        print(cmd)
        os.system(cmd)
        if not os.path.exists(img_output_path):
            print("Failed at 5s, now try at 0s.")
            cmd = 'ffmpeg -i "{}" -ss 00:00:00.000 -vframes 1 -vf scale=640:-1 "{}"'.format(
                p, img_output_path
            )
            print(cmd)
            os.system(cmd)
        return img_output_path


def delete(path):
    parent, fn = os.path.split(path)
    if not os.path.exists(path):
        print(path, "do not exists!")
        return
    if not os.path.exists(os.path.join(parent, ".trash")):
        os.mkdir(os.path.join(parent, ".trash"))
    print("del", path)
    shutil.move(path, os.path.join(parent, ".trash", fn))
    if parent in file_list_cache:
        del file_list_cache[parent]


load_cache()
