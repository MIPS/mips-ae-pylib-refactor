#!/usr/bin/env python3

import requests
import uuid
import json
from datetime import datetime
import time
import os
import sys
import argparse
from InquirerPy import prompt
import tarfile


class AtlasConstants:
    AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"
    CONFIG_ENVAR = "MIPS_ATLAS_CONFIG"


class AtlasConfig:
    def __init__(self, readonly=False):
        if AtlasConstants.CONFIG_ENVAR in os.environ:
            envvarval = os.environ[AtlasConstants.CONFIG_ENVAR]
            data = envvarval.split(":")
            self.apikey = data[0]
            self.channel = data[1]
            self.region = data[2]
            if not readonly:
                self.setGWbyChannelRegion()
        else:
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
                    self.hasConfig = True
                    if not readonly:
                        self.setGWbyChannelRegion()
            else:
                self.hasConfig = False

    def setGWbyChannelRegion(self):
        print("setting up selected gateway")
        url = AtlasConstants.AE_GLOBAL_API + "/gwbychannelregion"
        myobj = {
            "apikey": self.apikey,
            "channel": self.channel,
            "region": self.region,
        }
        x = requests.get(url, headers=myobj)
        self.gateway = x.json()["endpoint"]
        print("gateway has been set")


class SummaryReport:
    def __init__(self, jsonfile):
        with open(jsonfile) as f:
            self.summarydata = json.load(f)
            perfreport = self.summarydata["Statistics"]["Summary Performance Report"]
            self.totalcycles = perfreport["Total Cycles Consumed"]["val"]
            i = 0


class AtlasExplorer:
    AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"

    def __init__(self):
        # check env var,  then check file..etc.

        self.config = AtlasConfig()
        if not self.config.hasConfig:
            print(
                "Cloud connection is not setup. Please run `atlasexplorer.py configure`"
            )
            sys.exit(1)

    def setRootExperimentDirectory(self, path):
        """Sets the path where to place the results from the experiments you run"""
        self.rootpath = os.path.abspath(path)
        if not os.path.exists(path):
            os.mkdir(path)

    def __uploadConfig(self, url, content):
        print("uploading config")
        resp = requests.put(url, data=content)
        return resp.content

    def __uploadElfFile(self, url, elfPath):
        print("uploading elf file")
        with open(elfPath, "rb") as f:
            file_content = f.read()

        headersObj = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(file_content)),
        }
        resp = requests.put(url, data=file_content, headers=headersObj)
        return resp.content

    def __getStatus(self, url):
        x = requests.get(url)
        return x.json()

    def __downloadBinaryFile(self, url, targetPath, targetFile):
        response = requests.get(url, stream=True)
        with open(targetPath + "/" + targetFile, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

    # returns signed urls for report/statusget, grrput
    def __creatReport(self, reporttype, expconfig, datetime):
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

        url = self.config.gateway + "/createsignedurls"
        myobj = {
            "apikey": self.config.apikey,
            "channel": self.config.channel,
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
        uploadReportResp = self.__uploadConfig(reportCfgURL, reportConfigJson)

        grrDict = {
            "data": "todo timestamp",
        }
        grrJson = json.dumps(grrDict)
        # upload report request file to trigger start of report
        print("uploading report request file")
        grrResp = self.__uploadConfig(grrPutURL, grrJson)
        count = 0
        while count < 10:
            count += 1
            time.sleep(2)  # Pause for 1 second
            status = self.__getStatus(reportStatusURL)
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
                        self.__downloadBinaryFile(url, reportpath, name)

                # self.downloadZSTF(zstfFileURL, elf+'.zstf')
                # zstfsuccess = True
                break
            elif status["code"] == 500:
                print("error generating report(s), escaping now")
                break

    def createExperiment(self, elf, core, unpack):
        """Create an experiement using an elf file(path) and a selected core"""

        self.unpack = unpack
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

        url = self.config.gateway + "/createsignedurls"
        myobj = {
            "apikey": self.config.apikey,
            "channel": self.config.channel,
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
        cfgresp = self.__uploadConfig(cfgURL, configJson)
        elfresp = self.__uploadElfFile(elfURL, elf)

        count = 0
        zstfsuccess = False
        while count < 10:
            count += 1
            time.sleep(2)  # Pause for 1 second
            status = self.__getStatus(statusURL)
            if status["code"] == 100:
                print("zstf file is being generated...")
            if status["code"] == 200:
                print("zstf file is complete, downloading file now")
                self.__downloadBinaryFile(zstfFileURL, expdir, elf + ".zstf")
                zstfsuccess = True
                break
            elif status["code"] == 500:
                print("error genterating zstf, escaping now")
                break

        # kick of summary report
        if zstfsuccess:
            self.__creatReport("summary", configDict, now)
        # self.__creatReport("inst_counts", configDict, now)
        # self.__creatReport("inst_trace", configDict, now)

        print("experiment generation complete")

        if self.unpack:
            print("Unpacking reports")
            reportnames = ["summary", "inst_counts", "inst_trace"]
            expdir = formatted_string

            for report in reportnames:
                print("unpacking report: " + report)
                reporttar = os.path.join(
                    self.rootpath, expdir, report, "report_results.tar.gz"
                )
                if os.path.exists(reporttar):
                    destdir = os.path.join(self.rootpath, expdir, report)
                    with tarfile.open(reporttar, "r:gz") as tar:
                        tar.extractall(destdir)
                        tar.close()
                else:
                    print("report does not exist!!, skipped " + report)

            summaryjson = os.path.join(self.rootpath, expdir, "summary", "summary.json")
            if os.path.exists(summaryjson):
                summaryreport = SummaryReport(summaryjson)

        return formatted_string


# # end class def


AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"


def __getChannelList(apikey):
    url = AE_GLOBAL_API + "/channellist"
    myobj = {"apikey": apikey, "extversion": "0.0.24"}
    x = requests.get(url, headers=myobj)
    return x.json()


def __getUserValid(apikey):
    url = AE_GLOBAL_API + "/user"
    myobj = {"apikey": apikey}
    x = requests.get(url, headers=myobj)
    return x.status_code == 200


def configure(args):
    """Main program"""

    config = AtlasConfig(True)

    defkey = ""
    if config.hasConfig:
        defkey = config.apikey

    question_apikey = [
        {
            "type": "input",
            "name": "apikey",
            "default": defkey,
            "message": "Enter your api key:",
        },
    ]

    answers = prompt(question_apikey)
    apikey = answers["apikey"]

    if __getUserValid(apikey):
        chlist = __getChannelList(apikey)["channels"]
        chnamellist = []
        for ch in chlist:
            chnamellist.append(ch["name"])

        if len(chnamellist) > 1:
            defch = ""
            if config.hasConfig:
                defch = config.channel

            question_channel = [
                {
                    "type": "list",
                    "name": "channel",
                    "default": defch,
                    "message": "Please select a channel?",
                    "choices": chnamellist,
                }
            ]
            # get the channels for this user.
            chanswer = prompt(question_channel)["channel"]
        else:
            chanswer = chnamellist[0]
            print("Channel is automatically set to: " + chanswer)

        # get the region for the channel from the list above.
        regionlist = []
        for ch in chlist:
            if ch["name"] == chanswer:  # find the channel , extract regions into a list
                for reg in ch["regions"]:
                    regionlist = json.loads(ch["regions"])
                    break

        if len(regionlist) > 1:
            defreg = ""
            if config.hasConfig:
                defreg = config.region

            question_region = [
                {
                    "type": "list",
                    "name": "region",
                    "default": defreg,
                    "message": "Please select a region?",
                    "choices": regionlist,
                }
            ]

            regionanswer = prompt(question_region)["region"]
        else:
            regionanswer = regionlist[0]
            print("Region is automatically set to: " + regionanswer)

        config = {
            "apikey": apikey,
            "channel": chanswer,
            "region": regionanswer,
        }

        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, ".config", "mips", "atlaspy")
        config_file = os.path.join(config_dir, "config.json")

        os.makedirs(config_dir, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)

        print("Your configuration details are stored here:\n   " + config_file)
        print("For CI you may set an enviroment variable:")
        print(
            f"   MIPS_ATLAS_CONFIG = {config['apikey']}:{config['channel']}:{config['region']}"
        )
        print("You have your Atlas and are ready to go Exploring!")
    else:
        print("Invalid API Key")


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
