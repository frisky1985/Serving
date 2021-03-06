# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=doc-string-missing

from __future__ import unicode_literals, absolute_import
import os
import sys
import time
import requests
import json
import base64
from paddle_serving_client import Client
from paddle_serving_client.utils import MultiThreadRunner
from paddle_serving_client.utils import benchmark_args
from paddle_serving_app.reader import Sequential, URL2Image, Resize
from paddle_serving_app.reader import CenterCrop, RGB2BGR, Transpose, Div, Normalize

args = benchmark_args()

seq_preprocess = Sequential([
    URL2Image(), Resize(256), CenterCrop(224), RGB2BGR(), Transpose((2, 0, 1)),
    Div(255), Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225], True)
])


def single_func(idx, resource):
    file_list = []
    for file_name in os.listdir("./image_data/n01440764"):
        file_list.append(file_name)
    img_list = []
    for i in range(1000):
        img_list.append(open("./image_data/n01440764/" + file_list[i]).read())
    profile_flags = False
    if "FLAGS_profile_client" in os.environ and os.environ[
            "FLAGS_profile_client"]:
        profile_flags = True
    if args.request == "rpc":
        reader = ImageReader()
        fetch = ["score"]
        client = Client()
        client.load_client_config(args.model)
        client.connect([resource["endpoint"][idx % len(resource["endpoint"])]])
        start = time.time()
        for i in range(1000):
            if args.batch_size >= 1:
                feed_batch = []
                i_start = time.time()
                for bi in range(args.batch_size):
                    img = seq_preprocess(img_list[i])
                    feed_batch.append({"image": img})
                i_end = time.time()
                if profile_flags:
                    print("PROFILE\tpid:{}\timage_pre_0:{} image_pre_1:{}".
                          format(os.getpid(),
                                 int(round(i_start * 1000000)),
                                 int(round(i_end * 1000000))))

                result = client.predict(feed=feed_batch, fetch=fetch)
            else:
                print("unsupport batch size {}".format(args.batch_size))

    elif args.request == "http":
        py_version = sys.version_info[0]
        server = "http://" + resource["endpoint"][idx % len(resource[
            "endpoint"])] + "/image/prediction"
        start = time.time()
        for i in range(1000):
            if py_version == 2:
                image = base64.b64encode(
                    open("./image_data/n01440764/" + file_list[i]).read())
            else:
                image = base64.b64encode(open(image_path, "rb").read()).decode(
                    "utf-8")
            req = json.dumps({"feed": [{"image": image}], "fetch": ["score"]})
            r = requests.post(
                server, data=req, headers={"Content-Type": "application/json"})
    end = time.time()
    return [[end - start]]


if __name__ == '__main__':
    multi_thread_runner = MultiThreadRunner()
    endpoint_list = ["127.0.0.1:9393"]
    #endpoint_list = endpoint_list + endpoint_list + endpoint_list
    result = multi_thread_runner.run(single_func, args.thread,
                                     {"endpoint": endpoint_list})
    #result = single_func(0, {"endpoint": endpoint_list})
    avg_cost = 0
    for i in range(args.thread):
        avg_cost += result[0][i]
    avg_cost = avg_cost / args.thread
    print("average total cost {} s.".format(avg_cost))
