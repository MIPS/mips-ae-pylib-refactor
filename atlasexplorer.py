#!/usr/bin/env python3

import requests
import uuid
import json
from datetime import datetime
import time
import os
import argparse
from InquirerPy import prompt


class AtlasExplorer:
    AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"

    def __init__(self):
        # check env var,  then check file..etc.
        # print(os.environ['HOME'])
        # file first,
        home_dir = os.path.expanduser("~")
        path_parts = [home_dir, ".config", "mips", "atlastpy", "config.json"]
        configfile = os.path.join(*path_parts)
        if os.path.exists(configfile):
            with open(configfile) as f:
                data = json.load(f)
                self.apikey = data["apikey"]
                self.channel = data["channel"]
                self.region = data["region"]
                self.setGWbyChannelRegion()
        else:
            print("No configuration found, please run 'configure' command")

    def setRootExperimentDirectory(self, path):
        self.rootpath = path
        if not os.path.exists(path):
            os.mkdir(path)

    # def getChannelList(self):
    #    url = self.AE_GLOBAL_API + "/channellist"
    #    myobj = {"apikey": self.apikey, "extversion": "0.0.24"}
    #    x = requests.get(url, headers=myobj)
    #    return x.json()

    def validateApiKey(self):
        url = self.AE_GLOBAL_API + "/validateapikey"
        myobj = {"apikey": self.apikey}
        x = requests.get(url, headers=myobj)
        return x.json()

    # def getUserValid(self):
    #    url = self.AE_GLOBAL_API + "/user"
    #    myobj = {"apikey": self.apikey}
    #    x = requests.get(url, headers=myobj)
    #    return x.status_code == 200

    def setGWbyChannelRegion(self):
        print("setting up selected gateway")
        url = self.AE_GLOBAL_API + "/gwbychannelregion"
        myobj = {"apikey": self.apikey, "channel": self.channel, "region": self.region}
        x = requests.get(url, headers=myobj)
        self.gateway = x.json()["endpoint"]
        print("gateway has been set")

    def uploadConfig(self, url, content):
        print("uploading config")
        resp = requests.put(url, data=content)
        return resp.content

    def uploadElfFile(self, url, elfPath):
        print("uploading elf file")
        with open(elfPath, "rb") as f:
            file_content = f.read()

        headersObj = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(file_content)),
        }
        resp = requests.put(url, data=file_content, headers=headersObj)
        return resp.content

    def getStatus(self, url):
        x = requests.get(url)
        return x.json()

    def downloadBinaryFile(self, url, targetPath, targetFile):
        response = requests.get(url, stream=True)
        with open(targetPath + "/" + targetFile, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

    def downloadTextFile(self, url, targetFile):
        response = requests.get(url, stream=True)
        with open(targetFile, "w") as f:
            f.write(response.text)

    # returns signed urls for report/statusget, grrput
    def creatReport(self, reporttype, expconfig, datetime):
        print("creating report " + reporttype)
        formatted_string = datetime.strftime("%y%m%d-%H%M%S")
        reportuuid = formatted_string + "_" + str(uuid.uuid4())
        print("reportUUID: " + reportuuid)

        reportConfigDict = {
            "startDate": formatted_string,
            "reportUUID": reportuuid,
            "expUUID": expconfig["uuid"],  # expuuid,
            "core": expconfig["core"],
            "elf": expconfig["elf"],
            "reportName": reporttype,
            "reportType": reporttype,
            "userParameters": [],
            "startInst": 1,
            "endInst": -1,
            "resolution": 1,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": "0.0.53",  # ext version
        }

        rblob = {}
        rblob["data"] = reportConfigDict
        reportConfigJson = json.dumps(rblob)

        url = self.gateway + "/createsignedurls"
        myobj = {
            "apikey": self.apikey,
            "channel": self.channel,
            "exp-uuid": expconfig["uuid"],
            "action": "report",
        }
        resp = requests.post(
            url, json=reportConfigDict, headers=myobj
        )  # fetch the presigned url
        reportCfgURL = resp.json()["reporturl"]
        reportStatusURL = resp.json()["statusget"]
        grrPutURL = resp.json()["grrput"]

        # upload report cfg file,
        print("uploading report config")
        uploadReportResp = self.uploadConfig(reportCfgURL, reportConfigJson)

        grrDict = {
            "data": "todo timestamp",
        }
        grrJson = json.dumps(grrDict)
        # upload report request file to trigger start of report
        print("uploading report request file")
        grrResp = self.uploadConfig(grrPutURL, grrJson)
        count = 0
        while count < 10:
            count += 1
            time.sleep(2)  # Pause for 1 second
            status = self.getStatus(reportStatusURL)
            if status["code"] == 100:
                print("report " + reporttype + " is being generated")
            if status["code"] == 200:
                print("report " + reporttype + " is ready")
                # down load results
                for report in status["metadata"]["reports"]:
                    name = report["name"]
                    url = report["url"]
                    type = report["type"]

                    if type == "stream":
                        reportpath = self.expdir + "/" + reporttype
                        os.mkdir(reportpath)
                        self.downloadBinaryFile(url, reportpath, name)

                # self.downloadZSTF(zstfFileURL, elf+'.zstf')
                # zstfsuccess = True
                break
            elif status["code"] == 500:
                print("error generating report(s), escaping now")
                break

    # apikey, channel, action=experiment exp-uuid, workload
    def createExperiment(self, elf, core):
        print("creating experiment")

        if not os.path.exists(elf):
            print("elf does not exist, please check path")
            return

        # todo check core value
        # generate exp uuid,
        now = datetime.now()  # Get current datetime
        formatted_string = now.strftime("%y%m%d-%H%M%S")
        expuuid = formatted_string + "_" + str(uuid.uuid4())
        print("expUUID: " + expuuid)

        expdir = self.rootpath + "/" + formatted_string
        os.mkdir(expdir)
        self.expdir = expdir

        url = self.gateway + "/createsignedurls"
        myobj = {
            "apikey": self.apikey,
            "channel": self.channel,
            "exp-uuid": expuuid,
            "workload": elf,
            "core": core,
            "action": "experiment",
        }
        resp = requests.post(url, headers=myobj)  # fetch the presigned url

        cfgURL = resp.json()["cfgurl"]
        elfURL = resp.json()["elfurl"]
        statusURL = resp.json()["statusget"]
        zstfFileURL = resp.json()["zstffile"]

        configDict = {
            "core": core,
            "elf": elf,
            "uuid": expuuid,
            "localISS": False,
            "localSimulator": False,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": "0.0.53",  # ext version
        }

        configJson = json.dumps(configDict)
        cfgresp = self.uploadConfig(cfgURL, configJson)
        elfresp = self.uploadElfFile(elfURL, elf)

        count = 0
        zstfsuccess = False
        while count < 10:
            count += 1
            time.sleep(2)  # Pause for 1 second
            status = self.getStatus(statusURL)
            if status["code"] == 100:
                print("zstf file is being generated...")
            if status["code"] == 200:
                print("zstf file is complete, downloading file now")
                self.downloadBinaryFile(zstfFileURL, expdir, elf + ".zstf")
                zstfsuccess = True
                break
            elif status["code"] == 500:
                print("error genterating zstf, escaping now")
                break

        # kick of summary report
        if zstfsuccess:
            self.creatReport("summary", configDict, now)
            self.creatReport("inst_counts", configDict, now)
            self.creatReport("inst_trace", configDict, now)

        print("experiment complete")
        return formatted_string


# # end class def


AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"


def getChannelList(apikey):
    url = AE_GLOBAL_API + "/channellist"
    myobj = {"apikey": apikey, "extversion": "0.0.24"}
    x = requests.get(url, headers=myobj)
    return x.json()


def getUserValid(apikey):
    url = AE_GLOBAL_API + "/user"
    myobj = {"apikey": apikey}
    x = requests.get(url, headers=myobj)
    return x.status_code == 200


def configure(args):
    """Main program"""
    # print("this is main: " + args.login)
    question_apikey = [
        {"type": "input", "name": "apikey", "message": "Enter your api key:"},
        # {
        #     'type': 'list',
        #     'name': 'channel',
        #     'message': 'Please select a channel?',
        #     'choices': ['development', 'pr3']
        # },
        #  {
        #     'type': 'list',
        #     'name': 'region',
        #     'message': 'Please select a region?',
        #     'choices': ['us-west-2', 'us-east-1']
        # }
    ]

    answers = prompt(question_apikey)

    # myinst = AtlasExplorer(answers["apikey"])

    if getUserValid(answers["apikey"]):
        chlist = getChannelList(answers["apikey"])["channels"]
        chnamellist = []
        for ch in chlist:
            chnamellist.append(ch["name"])

        question_channel = [
            {
                "type": "list",
                "name": "channel",
                "message": "Please select a channel?",
                "choices": chnamellist,
            }
        ]
        # get the channels for this user.
        chanswer = prompt(question_channel)

        # get the region for the channel from the list above.
        regionlist = []
        for ch in chlist:
            if (
                ch["name"] == chanswer["channel"]
            ):  # find the channel , extract regions into a list
                for reg in ch["regions"]:
                    regionlist = json.loads(ch["regions"])
                    break

        question_region = [
            {
                "type": "list",
                "name": "region",
                "message": "Please select a region?",
                "choices": regionlist,
            }
        ]

        regionanswer = prompt(question_region)

        config = {
            "apikey": answers["apikey"],
            "channel": chanswer["channel"],
            "region": regionanswer["region"],
        }

        print("storing your configuration in home directory")
        home_dir = os.path.expanduser("~")
        print(home_dir)
        if not os.path.exists(home_dir + "/.config/mips"):
            os.mkdir(home_dir + "/.config/mips")

        configdir = home_dir + "/.config/mips/atlastpy/"
        if not os.path.exists(configdir):
            os.mkdir(configdir)

        with open(configdir + "/config.json", "w") as f:
            json.dump(config, f, indent=4)

        print(
            "If you wish, you may set a enviroment variable 'MIPS_ATLAS_EXP_CONFIG' to the following string: "
        )
        print(config)
    else:
        print("invalid api key")


def subcmd_configure(subparsers):
    parser = subparsers.add_parser(
        "configure",
        help="Configure Atlas Explorer Cloud Access",
    )
    parser.set_defaults(handler_function="configure")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="atlasexplorer",
        description="Atlas Explorer Utility",
    )

    subparsers = parser.add_subparsers(help="subcommand help", required=True)

    subcmd_configure(subparsers)

    args = parser.parse_args()

    # Execute provided subcommand
    eval(args.handler_function + "(args)")
