#!/usr/bin/python3

from flask import (
    Flask,
    render_template,
    send_file,
    redirect,
    request,
    send_from_directory,
    Response
)
import os
from os.path import join
from urllib.parse import unquote, quote
from math import ceil, floor

import utils, config

app = Flask(__name__)

def set_cache(response):
    if(type(response)==str):
        response = Response(response)
    response.cache_control.max_age = 3600
    response.cache_control.public = True
    if "no-cache" in response.cache_control:
        del response.cache_control["no-cache"]
    return response

@app.route("/")
def rd():
    return redirect("/" + config.url_base)


@app.route("/" + config.url_base + "/static/<path>")
def static_(path):
    # print(path)
    return set_cache(send_from_directory("static", path))


@app.route("/" + config.url_base + "/gv3.webmanifest")
def pwa():
    return set_cache(send_from_directory("static", "gv3.webmanifest"))


@app.route("/" + config.url_base + "/")
def index():
    return set_cache(render_template("frame.html", base=config.url_base))


@app.route("/" + config.url_base + "/tree/")
def root():
    return tree("")


def star():
    param = utils.get_param("star")
    star_list = list(utils.star_list)
    if "p" in request.args:
        p = int(request.args["p"])
        param["index"] = p
    else:
        p = param["index"]
    misc = {
        "index": [
            p,
            ceil(len(utils.star_list) / config.items_per_page),
        ],
        "current": "star",
        "parent": "",
        "base": config.url_base,
        "dark": config.dark,
        "tree": [],
        "sort": param["sort"],
        "r": param["r"],
        "filter_on": False,
        "filter": "",
        "scroll": param["scroll"],
    }
    if set(utils.star_list_sort_cache[param["sort"]]) != utils.star_list:
        if param["sort"] == "name":
            star_list.sort()
        elif param["sort"] == "date":
            star_list.sort(key=lambda x: utils.star_added_date[x])
        elif param["sort"] == "size":
            star_list.sort(key=lambda x: os.path.getsize(os.path.join(config.base, x)))
        elif param["sort"] == "rand":
            utils.random.shuffle(star_list)
        utils.star_list_sort_cache[param["sort"]] = star_list
    else:
        star_list = utils.star_list_sort_cache[param["sort"]]
    if param["r"]:
        star_list = star_list[::-1]

    items = {"dirs": [], "files": []}

    for fp in star_list[p * config.items_per_page : (p + 1) * config.items_per_page]:
        items["files"].append(
            # (quote(fp) + "?from_star", os.path.split(fp)[-1], not utils.is_img(fp))
            (quote(fp), os.path.split(fp)[-1], not utils.is_img(fp))
        )
    return render_template(
        "tree.html",
        items=items,
        misc=misc,
        max=max,
        min=min,
        enumerate=enumerate,
        len=len,
    )


@app.route("/" + config.url_base + "/tree/<path:path>")
def tree(path):
    if path == "star" or path == "star/":
        return star()

    path = unquote(path)
    # print("Listing", path)
    param = utils.get_param(path)
    fp = join(config.base, path)
    if "p" in request.args:
        p = int(request.args["p"])
        param["index"] = p
    else:
        p = param["index"]
    try:
        dir_content = utils.listdir(fp, param["sort"], param["r"])[
            p * config.items_per_page : (p + 1) * config.items_per_page
        ]
    except:
        raise
    parent = join(*(os.path.split(path)[:-1]))
    p_fp = join(config.base, parent)
    try:
        parent_param = utils.get_param(parent)
        # print(utils.listdir(p_fp, parent_param["sort"], parent_param["r"]))
        location_in_p = floor(
            utils.listdir(p_fp, parent_param["sort"], parent_param["r"]).index(
                os.path.split(path)[-1]
            )
            / config.items_per_page
        )
    except:
        # raise
        location_in_p = 0
    items = {"dirs": [], "files": []}
    misc = {
        "index": [
            p,
            ceil(len(utils.listdir(join(config.base, path))) / config.items_per_page),
        ],
        "current": quote(path),
        "parent": parent + "?p=" + str(location_in_p),
        "base": config.url_base,
        "dark": config.dark,
        "tree": [],
        "sort": param["sort"],
        "r": param["r"],
        "filter_on": fp in utils.filters,
        "filter": utils.filters[fp] if fp in utils.filters else "",
        "scroll": param["scroll"],
    }
    # print("-" * 100, misc)
    for i in dir_content:
        # i = quote(i,encoding="utf-8" )
        try:
            if os.path.isdir(join(config.base, path, i)):
                items["dirs"].append(
                    (
                        quote(join(path, i)),
                        i,
                        len(utils.listdir(join(config.base, path, i))),
                    )
                )
            else:
                items["files"].append((quote(join(path, i)), i, not utils.is_img(i), i.endswith(".mview")))
        except:
            raise
    if path == "":
        items["dirs"].append(("star", "Bookmarks", len(utils.star_list)))
    tree_s = path.split("/")
    for i in range(len(tree_s)):
        if not tree_s[i]:
            continue
        misc["tree"].append((tree_s[i], join(*tree_s[: i + 1])))
    # print(misc["tree"])
    utils.param_cache[path] = param
    return render_template(
        "tree.html",
        items=items,
        misc=misc,
        max=max,
        min=min,
        enumerate=enumerate,
        len=len,
    )


@app.route("/" + config.url_base + "/view/<path:path>")
def view(path):
    path = unquote(path)
    fp = join(config.base, path)
    if path.endswith(".mview"):
        return render_template("mview.html", file=path, base=config.url_base)
    if "from_star" in request.args and path in utils.star_list:
        star_list = list(utils.star_list)
        param = utils.get_param("star")
        if set(utils.star_list_sort_cache[param["sort"]]) != utils.star_list:
            if param["sort"] == "name":
                star_list.sort()
            elif param["sort"] == "date":
                star_list.sort(key=lambda x: utils.star_added_date[x])
            elif param["sort"] == "size":
                star_list.sort(
                    key=lambda x: os.path.getsize(os.path.join(config.base, x))
                )
            elif param["sort"] == "rand":
                utils.random.shuffle(star_list)
            utils.star_list_sort_cache[param["sort"]] = star_list
        else:
            star_list = utils.star_list_sort_cache[param["sort"]]
        if param["r"]:
            star_list = star_list[::-1]
        star_index = star_list.index(path)
        n = star_index % config.items_per_page
        misc = {
            "index": [star_index, len(utils.star_list)],
            "current": quote(path),
            "prev": quote(star_list[max(star_index - 1, 0)]) + "?from_star",
            "next": quote(star_list[min(star_index + 1, len(utils.star_list) - 1)])
            + "?from_star",
            "parent": "star?p=" + str(floor(star_index / config.items_per_page)),
            "base": config.url_base,
            "dark": config.dark,
            "img": utils.is_img(path),
            "og": config.resample,
            "name": os.path.split(path)[-1],
            "star": 1,
            "vol": utils.vol,
            "n": n,
        }
    else:
        parent = join(*(os.path.split(path)[:-1]))
        param = utils.get_param(parent)
        full_dir = utils.listdir(join(config.base, parent), param["sort"], param["r"])
        file_dir = [i for i in full_dir if utils.is_media(i)]

        file_index = file_dir.index(os.path.split(path)[-1])
        try:
            location_index = full_dir.index(os.path.split(path)[-1])
            n = location_index % config.items_per_page
            location_in_p = floor(location_index / config.items_per_page)
        except:
            location_index = 0
            location_in_p = 0
            n = 0
        misc = {
            "index": [file_index, len(file_dir)],
            "current": quote(path),
            "prev": quote(join(parent, file_dir[max(file_index - 1, 0)])),
            "next": quote(
                join(parent, file_dir[min(file_index + 1, len(file_dir) - 1)])
            ),
            "parent": quote(parent) + "?p=" + str(location_in_p),
            "base": config.url_base,
            "dark": config.dark,
            "img": utils.is_img(path),
            "og": config.resample,
            "name": os.path.split(path)[-1],
            "star": path in utils.star_list,
            "vol": utils.vol,
            "n": n
        }
    if param["fit"] >= 0:
        misc["scale_type_overwrite"] = param["fit"]
    return render_template(
        "view.html", misc=misc, max=max, min=min, enumerate=enumerate
    )


@app.route("/" + config.url_base + "/file/<path:path>")
def file(path):
    path = unquote(path)
    fp = join(config.base, path)
    return set_cache(send_file(fp))


@app.route("/" + config.url_base + "/delete/<path:path>")
def delete(path):
    path = unquote(path)
    utils.delete(join(config.base, path))
    return "OK"


@app.route("/" + config.url_base + "/thumb/<path:path>")
def thumb(path, depth=0):
    path = unquote(path)
    if path.endswith(".mview"):
        return set_cache(send_file("./static/icon.png"))
    if path == "star" or path == "star/":
        return set_cache(send_file("./static/star_holo.webp"))
    if "cache" in path:
        print("Warning! User should not have access to cache folder!")
        return set_cache(send_file("./static/folder.png"))
    if "size" in request.args:
        size = int(request.args["size"])
        # config.resample_size = size
    else:
        size = config.thumbnail_size
    fp = join(config.base, path)
    if os.path.isfile(fp):
        # return send_file("./static/folder.png")
        return set_cache(send_file(utils.thumbnails(fp, size), mimetype="image/jpeg"))
    elif len(utils.listdir(fp)) > 0:
        if utils.get_param(path)["r"]:
            selected = os.path.join(
                fp, utils.listdir(fp, sort_type=utils.get_param(path)["sort"])[-1]
            )
        else:
            selected = os.path.join(
                fp, utils.listdir(fp, sort_type=utils.get_param(path)["sort"])[0]
            )
        
        if selected.endswith(".mview"):
            return set_cache(send_file("./static/icon.png"))
        if utils.is_media(selected):
            return send_file(
                utils.thumbnails(selected, size),
                mimetype="image/jpeg",
            )
        else:
            if depth >= 0:
                return set_cache(send_file("./static/folder.png"))
            return thumb(selected, depth + 1)
    return set_cache(send_file("./static/folder.png"))


@app.route("/" + config.url_base + "/set_param/")
def set_param_c():
    return set_param("")


@app.route("/" + config.url_base + "/set_param/<path:path>")
def set_param(path):
    path = unquote(path)
    # print("ARGS:", request.args)
    if "clear_cache" in request.args:
        fp = join(config.base, path)
        if fp in utils.file_list_cache:
            del utils.file_list_cache[fp]
        return "OK"
    if "filter" in request.args:
        fp = join(config.base, path)
        if request.args["filter"]:
            utils.filters[fp] = request.args["filter"]
        else:
            if fp in utils.filters:
                del utils.filters[fp]
        return "OK"
    if "dark" in request.args:
        config.dark = int(request.args["dark"])
        return "OK"
    if "og" in request.args:
        config.resample = int(request.args["og"])
        return "OK"
    if "vol" in request.args:
        utils.vol = float(request.args["vol"])
        return "OK"
    # print(request.args)
    param = utils.get_param(path)
    if "fit" in request.args:
        param["fit"] = int(request.args["fit"])
        print("Set fit to", param["fit"])
    if "sort" in request.args:
        param["sort"] = request.args["sort"]
        print("Set sort to", param["sort"])
    if "r" in request.args:
        param["r"] = int(request.args["r"])
    if "scroll" in request.args:
        param["scroll"] = int(request.args["scroll"])
    if "star" in request.args:
        param["star"] = int(request.args["star"])
        if param["star"] == 1:
            utils.star_list.add(path)
            utils.star_added_date[path] = utils.time.time()
            utils.dump_cache(True)
        elif path in utils.star_list:
            utils.star_list.remove(path)
            utils.dump_cache(True)

    utils.param_cache[path] = param
    return "OK"


app.run(debug=False, port=config.port, host="0.0.0.0", threaded=True)
# app.run(debug=True, port=config.port, host="0.0.0.0", threaded=True)
