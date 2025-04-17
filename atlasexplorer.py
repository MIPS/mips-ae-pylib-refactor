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

API_EXT_VERSION = "0.0.68"  # changing this version may break the API, please check with the API team before changing this version.


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
            self.hasConfig = True
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

    def __checkWorkerStatus(self):
        print("Checking worker status")
        myobj = {
            "apikey": self.config.apikey,
            "channel": self.config.channel,
            "region": self.config.region,
        }
        resp = requests.get(self.config.gateway + "/dataworkerstatus", headers=myobj)
        return resp.json()

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
    def __creatReportNested(self, reporttype, expconfig, datetime):
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

        return reportConfigDict

    def createExperiment(self, elf, core, unpack):
        """Create an experiement using an elf file(path) and a selected core"""

        self.unpack = unpack
        print("creating experiment")

        if not os.path.exists(elf):
            print("elf does not exist, please check path")
            return

        """check worker status"""
        workerstatus = self.__checkWorkerStatus()
        if workerstatus["status"] is False:
            print("atlas explorer service is down, please try later")
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
        # zstfFileURL = resp.json()["zstffile"]

        configDict = {
            "core": core,
            "elf": elf,
            "uuid": expuuid,
            "localISS": False,
            "localSimulator": False,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": "0.0.53",  # ext version
            # "reports": [sumreport],
        }
        sumreport = self.__creatReportNested("summary", configDict, now)
        instcountreport = self.__creatReportNested("inst_counts", configDict, now)
        insttracereport = self.__creatReportNested("inst_trace", configDict, now)

        # Add an element to the existing configDict
        configDict["reports"] = [sumreport, instcountreport, insttracereport]

        configJson = json.dumps(configDict)
        cfgresp = self.__uploadConfig(cfgURL, configJson)
        elfresp = self.__uploadElfFile(elfURL, elf)

        count = 0

        while count < 10:
            count += 1
            time.sleep(2)  # Pause for 1 second
            status = self.__getStatus(statusURL)
            if status["code"] == 100:
                print("experiment is being generated")
            if status["code"] == 200:
                print("experiment is ready to downloading now")
                print("report " + "summary" + " is ready")
                # down load results
                result = status["metadata"]["result"]
                name = result["name"]
                url = result["url"]
                type = result["type"]

                if type == "stream":
                    #  reportpath = self.expdir + "/"  # + "summary"
                    #  os.mkdir(reportpath)
                    self.__downloadBinaryFile(url, self.expdir, name)
                break
            elif status["code"] == 500:
                print("error generating experiment, escaping now")
                break

        if self.unpack:
            print("Unpacking reports")
            expdir = formatted_string

            # for report in reportnames:
            # print("unpacking reports: " + report)
            reporttar = os.path.join(self.rootpath, expdir, "report_results.tar.gz")
            if os.path.exists(reporttar):
                destdir = os.path.join(self.rootpath, expdir)
                with tarfile.open(reporttar, "r:gz") as tar:
                    tar.extractall(destdir)
                    tar.close()
            else:
                print("report does not exist!!, skipped ")

            summaryjson = os.path.join(self.rootpath, expdir, "summary", "summary.json")
            if os.path.exists(summaryjson):
                summaryreport = SummaryReport(summaryjson)

        return formatted_string


# # end class def


AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"


def __getChannelList(apikey):
    global API_EXT_VERSION
    url = AE_GLOBAL_API + "/channellist"
    myobj = {"apikey": apikey, "extversion": API_EXT_VERSION}
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
