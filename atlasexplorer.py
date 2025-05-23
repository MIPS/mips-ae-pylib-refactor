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
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

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

    def __uploadExpPackage(self, url, content):
        print("uploading experiment package")

        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(
                os.path.getsize(content) if isinstance(content, str) else len(content)
            ),
        }
        with open(content, "rb") if isinstance(content, str) else content as data:
            resp = requests.put(url, data=data, headers=headers)
        return resp.content

    def __getStatus(self, url):
        x = requests.get(url)
        return x.json()

    def __downloadBinaryFile(self, url, targetPath, targetFile):
        response = requests.get(url, stream=True)
        with open(targetPath + "/" + targetFile, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

    def __hybrid_encrypt(self, public_key_pem: str, input_file: str):
        try:
            # Read the public key from PEM file
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),  # Convert the string to bytes
                backend=default_backend(),
            )

            input_path = Path(input_file)
            output_file = input_path.with_name("temp.enc")

            # Read file data
            with open(input_file, "rb") as f:
                file_data = f.read()

            # Generate random AES key and IV
            symmetric_key = get_random_bytes(32)  # 256 bits
            iv = get_random_bytes(16)

            cipher = Cipher(
                algorithms.AES(symmetric_key), modes.GCM(iv), backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Encrypt the file data
            encrypted_data = encryptor.update(file_data) + encryptor.finalize()
            # Get the authentication tag (required for GCM mode)
            auth_tag = encryptor.tag

            public_key = serialization.load_pem_public_key(
                public_key_pem.encode("utf-8"), backend=default_backend()
            )

            # Encrypt the symmetric key with the recipient's public key
            encrypted_symmetric_key = public_key.encrypt(
                symmetric_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            # Prepend IV, encrypted symmetric key, and authentication tag to the encrypted data
            output_buffer = iv + encrypted_symmetric_key + auth_tag + encrypted_data

            with open(output_file, "wb") as f:
                f.write(output_buffer)

            os.remove(input_file)
            os.rename(output_file, input_file)

            print("File encrypted using hybrid approach.")

        except Exception as error:
            print("Encryption error:", error)

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
            "elf": expconfig["workload"],
            "reportName": reporttype,
            "reportType": reporttype,
            "userParameters": [],
            "startInst": 1,
            "endInst": -1,
            "resolution": 1,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": "0.0.87",
            "isROIReport": False,
            "region": 0,
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

        # generate a config file and write it out.
        configDict = {
            "core": core,
            "elf": elf,
            "workload": elf,
            "uuid": expuuid,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": "0.0.87",  # ext version
            "compiler": "",
            "compilerFlags": "",
            "numRegions": 0,
            "reports": [],
            "heartbeat": "104723",
            "iss": "esesc",  # or 'imperas'
            "apikey": "",
            "geolocation": {},
        }

        sumreport = self.__creatReportNested("summary", configDict, now)
        instcountreport = self.__creatReportNested("inst_counts", configDict, now)
        insttracereport = self.__creatReportNested("inst_trace", configDict, now)

        configDict["reports"] = [sumreport, instcountreport, insttracereport]
        configDict["apikey"] = self.config.apikey

        with open(os.path.join(expdir, "config.json"), "w") as f:
            json.dump(configDict, f, indent=4)

        # Create a tar.gz file containing config.json and elf
        workload_tar_path = os.path.join(expdir, "workload.exp")
        with tarfile.open(workload_tar_path, "w:gz") as tar:
            tar.add(os.path.join(expdir, "config.json"), arcname="config.json")
            tar.add(elf, arcname=os.path.basename(elf))

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

        packageURL = resp.json()["exppackageurl"]
        publicKey = resp.json()["publicKey"]
        statusURL = resp.json()["statusget"]

        self.__hybrid_encrypt(publicKey, workload_tar_path)

        cfgresp = self.__uploadExpPackage(packageURL, workload_tar_path)
        count = 0
        # check the status of the experiment
        # 10 times, 2 sec apart
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
            elif status["code"] == 404:
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
