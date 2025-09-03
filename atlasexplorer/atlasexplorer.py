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
from Crypto.Random import get_random_bytes
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from Crypto.Protocol.KDF import scrypt
from elftools.elf.elffile import ELFFile
import re
import locale
from dotenv import load_dotenv


load_dotenv()

# changing this version may break the API, please check with the API team before changing this version.
API_EXT_VERSION = os.environ.get("API_EXT_VERSION", "0.0.97")


class Experiment:
    def __init__(self, expdir, atlas, verbose=True):
        self.verbose = verbose
        self.atlas = atlas
        """Setup the path where to place the results from the experiments you run"""
        self.expdir = os.path.abspath(expdir)
        if not os.path.exists(expdir):
            os.mkdir(expdir)
        self.config = None
        self.summary = None
        self.instcounts = None
        self.insttrace = None
        self.workloads = []
        self.core = None

        # Load the experiment configuration from config.json
        config_path = os.path.join(expdir, "config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.config = json.load(f)

        # Load the summary report if it exists

    def getRoot(self):
        """Returns the root directory of the experiment"""
        return self.expdir

    def getSummary(self):
        """Returns the summary report of the experiment"""
        if self.summary:
            return self.summary
        else:
            print("No summary report found for this experiment.")
            return None

    def __uploadExpPackage(self, url, content):
        if self.verbose:
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

            if self.verbose:
                print("File encrypted using hybrid approach.")

        except Exception as error:
            print("Encryption error:", error)

    def __decrypt_file_with_password(self, src_file_path: str, password: str):
        try:
            # Step 1: Read the encrypted file
            with open(src_file_path, "rb") as f:
                encrypted_data = f.read()

            # Step 2: Derive a 256-bit key from the password
            key = scrypt(password.encode(), salt=b"salt", key_len=32, N=16384, r=8, p=1)

            # Step 3: Create a decipher instance (AES-256-ECB mode, no IV)
            cipher = AES.new(key, AES.MODE_ECB)

            # Step 4: Decrypt the file data (remove PKCS#7 padding)
            decrypted_data = cipher.decrypt(encrypted_data)
            pad_len = decrypted_data[-1]
            if pad_len < 1 or pad_len > 16:
                raise ValueError("Invalid padding length.")
            decrypted_data = decrypted_data[:-pad_len]

            # Step 5: Write the decrypted data to a new file
            decrypted_file_path = src_file_path + ".decrypted"
            with open(decrypted_file_path, "wb") as f:
                f.write(decrypted_data)

            # Delete the encrypted file
            os.remove(src_file_path)
            # Rename the decrypted file to the original file name
            os.rename(decrypted_file_path, src_file_path)
        except Exception as error:
            print("Decryption error:", error)
            raise Exception(
                "Decryption failed. Please check the password and try again."
            )

    def snapshotSource(self, elfPath):
        source_files = set()

        if not elfPath or not os.path.exists(elfPath):
            if self.verbose:
                print(f"ELF path does not exist: {elfPath}")
            return set()

        try:
            with open(elfPath, "rb") as f:
                elffile = ELFFile(f)
                if elffile.has_dwarf_info():
                    dwarfinfo = elffile.get_dwarf_info()

                    for CU in dwarfinfo.iter_CUs():
                        try:
                            # Get compilation directory from the compilation unit
                            comp_dir = ""
                            top_die = CU.get_top_DIE()
                            if "DW_AT_comp_dir" in top_die.attributes:
                                comp_dir = top_die.attributes["DW_AT_comp_dir"].value
                                if isinstance(comp_dir, bytes):
                                    comp_dir = comp_dir.decode("utf-8")

                            lineprog = dwarfinfo.line_program_for_CU(CU)
                            if lineprog is None:
                                continue

                            # Extract file entries from line program
                            for file_entry in lineprog["file_entry"]:
                                try:
                                    filename = file_entry.name
                                    if isinstance(filename, bytes):
                                        filename = filename.decode("utf-8")

                                    # Get directory index and resolve directory
                                    dir_index = getattr(file_entry, "dir_index", 0)
                                    directory = ""

                                    if dir_index > 0 and "include_directory" in lineprog:
                                        include_dirs = lineprog["include_directory"]
                                        if dir_index <= len(include_dirs):
                                            # Build directory by appending include_directory entries up to dir_index
                                            directory_parts = []
                                            try:
                                                for i in range(dir_index + 1):
                                                    if i < len(include_dirs):
                                                        dir_part = include_dirs[i]
                                                        if isinstance(dir_part, bytes):
                                                            dir_part = dir_part.decode("utf-8")
                                                        directory_parts.append(dir_part)
                                                directory = (
                                                    os.path.join(*directory_parts)
                                                    if directory_parts
                                                    else ""
                                                )
                                            except (IndexError, ValueError) as e:
                                                if self.verbose:
                                                    print(f"Warning: Directory index issue in ELF file {elfPath}: {e}")
                                                directory = ""
                                            
                                            if isinstance(directory, bytes):
                                                directory = directory.decode("utf-8")

                                    # Build full path
                                    if directory:
                                        if os.path.isabs(directory):
                                            full_path = os.path.join(directory, filename)
                                        elif comp_dir:
                                            full_path = os.path.join(comp_dir, directory, filename)
                                        else:
                                            full_path = os.path.join(directory, filename)
                                    elif comp_dir:
                                        full_path = os.path.join(comp_dir, filename)
                                    else:
                                        full_path = filename

                                    source_files.add(full_path)
                                except Exception as e:
                                    if self.verbose:
                                        print(f"Warning: Error processing file entry in ELF {elfPath}: {e}")
                                    continue
                        except Exception as e:
                            if self.verbose:
                                print(f"Warning: Error processing compilation unit in ELF {elfPath}: {e}")
                            continue
        except Exception as e:
            if self.verbose:
                print(f"Warning: Error reading ELF file {elfPath}: {e}")
            return set()

        # Filter for existing files only
        if self.verbose:
            print("Embedded source files in ELF:")
        existing_source_files = set()
        for src in sorted(source_files):
            if os.path.exists(src):
                existing_source_files.add(src)
                if self.verbose:
                    print(src)

        return existing_source_files

    def getExperiment(self, expdir, atlas=None, verbose=True):
        """Returns an Experiment object for the given experiment directory"""
        if not os.path.exists(expdir):
            print("Experiment directory does not exist: " + expdir)
            return None
        # Use self.atlas if atlas is not provided
        if atlas is None:
            atlas = self.atlas
        return Experiment(expdir, atlas, verbose=verbose)

    def addWorkload(self, workload):
        """Adds a workload to the experiment"""
        if not os.path.exists(workload):
            print(f"Error: specified elf file does not exist\nELF: {workload}")
            sys.exit(1)
        self.workloads.append(workload)

    def setCore(self, core):
        """Sets the core for the experiment"""
        self.core = core
        if self.verbose:
            print("Core set to: " + core)

    def run(self, expname=None, unpack=True):
        """Creates an experiment with the given elf and core.
        elf: path to the elf file
        core: core name, e.g. I8500, P8500, etc.
        expname: name of the experiment, if None, it will be generated from the elf file name and timestamp
        unpack: if True, unpack the reports after the experiment is created
        """
        # check if wl is a list or a single string
        # if isinstance(workloads, str):
        #    workloads = [workloads]

        # for wl in workloads:
        #    if not os.path.exists(wl):
        #        print(f"Error: specified elf file does not exist\nELF: {wl}")
        #        sys.exit(1)

        # if not os.path.exists(workloads):
        #    print("Error: specified elf file does not exist\nELF: " + workloads)
        #    sys.exit(1)

        now = datetime.now()  # Get current datetime
        self.experiment_timestamp = now.strftime("%y%m%d_%H%M%S")

        if expname is None:
            expname = self.core + "_" + self.experiment_timestamp

        if self.verbose:
            print("experiment name is set to: " + expname)

        self.expname = expname
        self.unpack = unpack
        if self.verbose:
            print("creating experiment")

        expuuid = self.experiment_timestamp + "_" + str(uuid.uuid4())
        if self.verbose:
            print("expUUID: " + expuuid)

        expdir = os.path.join(self.expdir, expname)
        os.mkdir(expdir)
        self.expdir = expdir

        # Create an array of basenames from workloads
        workload_basenames = [os.path.basename(wl) for wl in self.workloads]

        # Create an array of objects with "elf" and "zstf" keys
        workload_objs = [{"elf": wl, "zstf": ""} for wl in self.workloads]
        # Set the absolute path to the elf file
        # generate a config file and write it out.
        date_string = now.strftime("%y%m%d_%H%M%S")
        experimentConfigDict = {
            "date": date_string,
            "name": expname,
            "core": self.core,
            "workload": workload_objs,  # workload_basenames,
            "uuid": expuuid,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": "0.0.97",  # ext version
            "compiler": "",
            "compilerFlags": "",
            "numRegions": 0,
            "reports": [],
            "heartbeat": "104723",
            "iss": "esesc",  # or 'imperas'
            "apikey": "",
            "geolocation": {},
            "otp": "".join([chr(x) for x in get_random_bytes(32)]),
            "version": "1.0.0",
            "arch": {
                "num_threads": 1,
            },
            "clientType": "python",
        }

        self.atlas._getCloudCaps(experimentConfigDict["toolsVersion"])

        versions = self.atlas.getVersionList()
        print("Available versions: " + ", ".join(versions))

        experimentConfigDict["arch"] = self.atlas.getCoreInfo(self.core)

        # for summary,  we don't need # elf and zstf names, so we can use empty strings
        sumreport = self.__creatReportNested(
            "summary", "", experimentConfigDict, "", ""
        )

        experimentConfigDict["reports"].append(sumreport)
        for wl_obj in workload_objs:
            elf_name = os.path.basename(wl_obj["elf"])
            zstf_name = os.path.basename(wl_obj["zstf"])

            if not zstf_name:
                zstf_name = elf_name + ".zstf"

            elf_base = elf_name[:-4] if elf_name.lower().endswith(".elf") else elf_name

            instcountreport = self.__creatReportNested(
                "inst_counts",
                elf_base + "_Instruction_Counts",
                experimentConfigDict,
                elf_name,
                zstf_name,
            )
            insttracereport = self.__creatReportNested(
                "inst_trace",
                elf_base + "_Instruction_Trace",
                experimentConfigDict,
                elf_name,
                zstf_name,
            )
            # Add the reports to the experimentConfigDict
            experimentConfigDict["reports"].append(instcountreport)
            experimentConfigDict["reports"].append(insttracereport)

        experimentConfigDict["apikey"] = self.atlas.config.apikey
        # print(json.dumps(experimentConfigDict, indent=4))
        with open(os.path.join(expdir, "config.json"), "w") as f:
            json.dump(experimentConfigDict, f, indent=4)

        # sys.exit(0)
        # Create a tar.gz file containing config.json and elf
        workload_tar_path = os.path.join(expdir, "workload.exp")
        with tarfile.open(workload_tar_path, "w:gz") as tar:
            tar.add(os.path.join(expdir, "config.json"), arcname="config.json")
            for wl in self.workloads:
                if os.path.exists(wl):
                    tar.add(wl, arcname=os.path.basename(wl))
                else:
                    sys.exit(1)  # If the workload file does not exist, exit with error
            # print(f"Warning: Workload file {wl} does not exist, skipping.")
            # tar.add(workloads, arcname=os.path.basename(workloads))

        # url = self.config.gateway + "/createsignedurls"
        # myobj = {
        #     "apikey": self.config.apikey,
        #     "channel": self.config.channel,
        #     "exp-uuid": expuuid,
        #     "workload": workloads,
        #     "core": core,
        #     "action": "experiment",
        # }
        # resp = requests.post(url, headers=myobj)  # fetch the presigned url
        resp = self.atlas.getSignedUrls(
            expuuid, expname, self.core
        )  # fetch the presigned url

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
                if self.verbose:
                    print("experiment is being generated.....")
            if status["code"] == 200:
                if self.verbose:
                    print("experiment is ready, downloading now")
                # down load results
                result = status["metadata"]["result"]
                name = result["name"]
                url = result["url"]
                type = result["type"]

                if type == "stream":
                    #  reportpath = self.expdir + "/"  # + "summary"
                    #  os.mkdir(reportpath)
                    self.__downloadBinaryFile(
                        url, self.expdir, self.expname + ".tar.gz"
                    )

                break
            elif status["code"] == 404:
                break
            elif status["code"] == 500:
                print("error generating experiment, escaping now")
                break

        if self.unpack:
            if self.verbose:
                print("Preparing download")
            expdir = expname

            # for report in reportnames:
            # print("unpacking reports: " + report)
            reporttar = os.path.join(self.expdir, self.expname + ".tar.gz")
            if os.path.exists(reporttar):
                if self.verbose:
                    print("Decrypting package")
                self.__decrypt_file_with_password(
                    reporttar, experimentConfigDict["otp"]
                )
                if self.verbose:
                    print("Unpacking package")
                destdir = self.expdir  # os.path.join(self.rootpath, expdir)
                with tarfile.open(reporttar, "r:gz") as tar:
                    # filter for tar, for python 3.12 and later
                    tar.extractall(destdir, filter='tar')
                    tar.close()
            else:
                print("package does not exist!!, skipped: " + reporttar)

            # Remove any summary ROI files that are not valid.
            self.cleanSummaries("summary")
            # self.cleanSummaries("summarythreads")

            summaryjson = os.path.join(
                self.expdir, expdir, "reports", "summary", "summary.json"
            )

            if os.path.exists(summaryjson):
                self.summary = SummaryReport(summaryjson)

            # Delete the workload_tar_path file after unpacking
            if os.path.exists(workload_tar_path):
                os.remove(workload_tar_path)

            for wl in experimentConfigDict["workload"]:
                elf_path = wl.get("elf")
                if elf_path and os.path.exists(elf_path):
                    self.snapshotSource(elf_path)

    def __creatReportNested(self, reporttype, reportName, expconfig, elfName, zstfName):
        if self.verbose:
            print("creating report " + reporttype)

        reportuuid = self.experiment_timestamp + "_" + str(uuid.uuid4())
        if self.verbose:
            print("reportUUID: " + reportuuid)

        reportConfigDict = {
            "startDate": self.experiment_timestamp,
            "reportUUID": reportuuid,
            "expUUID": expconfig["uuid"],  # expuuid,
            "core": expconfig["core"],
            "elfFileName": elfName,
            "zstfFileName": zstfName,
            "reportName": reportName,
            "reportType": reporttype,
            "userParameters": [],
            "startInst": 1,
            "endInst": -1,
            "resolution": 1,
            "toolsVersion": "latest",
            "timeout": 300,
            "pluginVersion": "0.0.97",
            "isROIReport": False,
            "region": 0,
        }

        return reportConfigDict

    def cleanSummaries(self, report):
        """Cleans up the summary reports that are not valid"""
        if not hasattr(self, "expdir"):
            print("No experiment directory set, please run createExperiment first")
            return

        summarydir = os.path.join(self.expdir, "reports", report)
        if not os.path.exists(summarydir):
            print("No report directory found:" + report)
            return

        for filename in os.listdir(summarydir):
            if "_roi_" in filename and filename.endswith(".json"):
                filepath = os.path.join(summarydir, filename)
                with open(filepath) as f:
                    summaryreport = SummaryReport(filepath)
                if summaryreport.totalcycles == 0 and summaryreport.totalinsts == 0:
                    if self.verbose:
                        print("Deleting invalid roi report: " + filepath)
                    os.remove(filepath)


# cmt to test workflow 11
class SummaryReport:
    def __init__(self, jsonfile):
        with open(jsonfile) as f:
            jsonData = json.load(f)
            self.summarydata = jsonData["Statistics"]["Summary Performance Report"]

            # Remove the "ordered_key" entry if it exists
            self.summarydata.pop("ordered_keys", None)

            self.totalcycles = self.summarydata["Total Cycles Consumed"]["val"]

            if "Total Instructions Retired" in self.summarydata:
                self.totalinsts = self.summarydata["Total Instructions Retired"]["val"]
            elif "Total Instructions Retired (All Threads)" in self.summarydata:
                self.totalinsts = self.summarydata[
                    "Total Instructions Retired (All Threads)"
                ]["val"]

    def getTotalCycles(self):
        """Returns the total cycles from the summary report"""
        return self.totalcycles

    def getTotalInstructions(self):
        """Returns the total instructions from the summary report"""
        return self.totalinsts

    def getMetricKeys(self, regex_pattern=None):
        """Returns a list of metric keys from the summary report, optionally filtered by regex pattern"""
        all_keys = list(self.summarydata.keys())

        if regex_pattern is None:
            return all_keys

        try:
            pattern = re.compile(regex_pattern)
            return [key for key in all_keys if pattern.search(key)]
        except re.error:
            print(f"Invalid regex pattern: {regex_pattern}")
            return all_keys

    def getMetricValue(self, key):
        """Returns the value of a specific metric key from the summary report"""
        return self.summarydata[key]["val"]

    def printMetrics(self, regex_pattern=None):
        """Prints all metrics in the summary report, optionally filtered by regex pattern"""
        keys = self.getMetricKeys(regex_pattern)
        locale.setlocale(locale.LC_ALL, "")
        for key in keys:
            value = self.getMetricValue(key)
            try:
                value_str = (
                    locale.format_string("%d", value, grouping=True)
                    if isinstance(value, int)
                    else str(value)
                )
            except Exception:
                value_str = str(value)
            print(f"{key}: {value_str}")


class AtlasConstants:
    AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"
    CONFIG_ENVAR = "MIPS_ATLAS_CONFIG"


class AtlasConfig:
    def __init__(
        self, readonly=False, verbose=True, apikey=None, channel=None, region=None
    ):
        self.verbose = verbose
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
            path_parts = [home_dir, ".config", "mips", "atlaspy", "config.json"]
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
            elif apikey and channel and region:
                # if no config file, but we have apikey, channel and region, set them.
                self.apikey = apikey
                self.channel = channel
                self.region = region
                self.hasConfig = True
                if not readonly:
                    self.setGWbyChannelRegion()
            else:
                self.hasConfig = False

    def setGWbyChannelRegion(self):
        """
        Sets the API gateway endpoint based on the current API key, channel, and region.
        Fetches the endpoint from the cloud and updates self.gateway.
        Handles network errors and unexpected responses gracefully.
        """
        if self.verbose:
            print("Setting up selected gateway...")
        url = AtlasConstants.AE_GLOBAL_API + "/gwbychannelregion"
        myobj = {
            "apikey": self.apikey,
            "channel": self.channel,
            "region": self.region,
        }
        try:
            response = requests.get(url, headers=myobj, timeout=10)
            response.raise_for_status()
            data = response.json()
            endpoint = data.get("endpoint")
            if not endpoint:
                raise ValueError("No 'endpoint' found in response from gateway API.")
            self.gateway = endpoint
            if self.verbose:
                print(f"Gateway has been set: {self.gateway}")
        except requests.RequestException as e:
            if 'response' in dir(e) and e.response is not None:
                print(f"Error connecting to gateway API: {e}\nStatus: {e.response.status_code}\nText: {e.response.text}")
            else:
                print(f"Error connecting to gateway API: {e}")
            self.gateway = None
        except ValueError as ve:
            print(f"Invalid response from gateway API: {ve}")
            self.gateway = None


class AtlasExplorer:
    AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"

    def __init__(self, apikey=None, channel=None, region=None, verbose=False):
        # Import and show deprecation warning for monolithic module usage
        try:
            from .utils.deprecation import show_monolithic_deprecation_warning
            show_monolithic_deprecation_warning("monolithic_class_initialization")
        except ImportError:
            # Fallback warning if deprecation module unavailable
            import warnings
            warnings.warn(
                "\n" + "="*60 + "\n"
                "🚨 DEPRECATION NOTICE: Atlas Explorer monolithic module is deprecated!\n"
                "🚀 Benefits: 101x faster imports, 99.7% memory efficiency improvement\n"
                "📖 Migration guide: https://docs.atlasexplorer.com/migration-guide\n"
                "💬 Support: migration-support@atlasexplorer.com\n"
                + "="*60 + "\n",
                UserWarning,
                stacklevel=2
            )
        
        # check env var,  then check file..etc.
        self.verbose = verbose
        self.config = AtlasConfig(
            verbose=verbose, apikey=apikey, channel=channel, region=region
        )
        if not self.config.hasConfig:
            print(
                "Cloud connection is not setup. Please run `atlasexplorer.py configure`"
            )
            sys.exit(1)

        # Check worker status only if gateway is set
        workerstatus = None
        if hasattr(self.config, "gateway") and self.config.gateway:
            workerstatus = self.__checkWorkerStatus()
            if workerstatus and workerstatus.get("status") is False:
                print("Error: atlas explorer service is down, please try later")
                sys.exit(1)
        else:
            if self.verbose:
                print("Warning: Gateway is not set. Skipping worker status check.")

    #  def setRootExperimentDirectory(self, path):
    #      """Sets the path where to place the results from the experiments you run"""
    #      self.rootpath = os.path.abspath(path)
    #      if not os.path.exists(path):
    #          os.mkdir(path)

    def _getCloudCaps(self, version):
        self.versionCaps = None
        self.channelCaps = None
        
        # Check if gateway is properly configured
        if self.config.gateway is None:
            print("Error: Gateway is not configured. Cannot fetch cloud capabilities.")
            print("This usually means there's an issue with the API service or your configuration.")
            print("Please run 'atlasexplorer.py configure' to reconfigure your settings.")
            sys.exit(1)
            
        url = self.config.gateway + "/cloudcaps"
        myobj = {
            "Content-Type": "application/json",
            "apikey": self.config.apikey,
        }
        resp = requests.get(url, headers=myobj)
        if resp.status_code != 200:
            print("Error fetching cloud capabilities: " + resp.text)
            sys.exit(1)

        self.channelCaps = resp.json()
        # print("Cloud capabilities:")
        # print(json.dumps(resp.json(), indent=4))

        # Iterate over the caps array and find the entry where "version" == version
        if isinstance(self.channelCaps, list):
            found = False
            for cap in self.channelCaps:
                if cap.get("version") == version:
                    # print(f"Capabilities for version {version}:")
                    # print(json.dumps(cap, indent=4))
                    found = True
                    self.versionCaps = cap
                    break
            if not found:
                print(f"No capabilities found for version {version}")
                sys.exit(1)

        else:
            print("Unexpected format for cloud capabilities response.")
            sys.exit(1)

    def getCoreInfo(self, core):
        if self.versionCaps is None:
            print("Cloud capabilities not fetched. Please run _getCloudCaps first.")
            return False

        arches = self.versionCaps.get("shinro").get("arches")
        if isinstance(arches, list):
            for arch in arches:
                if arch.get("name") == core:
                    return arch

        print(f"Core {core} is not supported by the cloud capabilities.")
        sys.exit(1)

    def getVersionList(self):
        """Returns a list of available versions from the cloud capabilities"""
        if self.channelCaps is None:
            print("Cloud capabilities not fetched. Please run _getCloudCaps first.")
            return []

            # print("Available versions in cloud capabilities:")
            # print(json.dumps(self.channelCaps, indent=4))
        if isinstance(self.channelCaps, list):
            return [version.get("version") for version in self.channelCaps]

        print("No architectures found in cloud capabilities.")
        return []

    def __checkWorkerStatus(self):
        """
        Checks the status of the Atlas Explorer worker via the cloud API.

        Returns:
            dict: The JSON response from the worker status endpoint, or a dict with error info if the request fails.

        Logging:
            - Prints detailed status and error messages, including HTTP status codes and exceptions.
        """
        if self.verbose:
            print("Checking worker status...")
        if not hasattr(self.config, "gateway") or not self.config.gateway:
            print("Error: Gateway is not set. Cannot check worker status.")
            return {"status": False, "error": "Gateway not set"}
        myobj = {
            "apikey": self.config.apikey,
            "channel": self.config.channel,
            "region": self.config.region,
        }
        url = self.config.gateway + "/dataworkerstatus"
        try:
            resp = requests.get(url, headers=myobj, timeout=10)
            if resp.status_code != 200:
                print(f"Error fetching worker status: {resp.status_code} {resp.text}")
                return {"status": False, "error": f"HTTP {resp.status_code}", "details": resp.text}
            result = resp.json()
            if self.verbose:
                print(f"Worker status response: {result}")
            return result
        except requests.RequestException as e:
            print(f"Exception during worker status fetch: {e}")
            return {"status": False, "error": str(e)}

    # returns signed urls for report/statusget, grrput

    def getSignedUrls(self, expuuid, name, core):
        """Returns signed URLs for the given experiment UUID, workloads, and core"""
        url = self.config.gateway + "/createsignedurls"
        myobj = {
            "apikey": self.config.apikey,
            "channel": self.config.channel,
            "exp-uuid": expuuid,
            "workload": name,
            "core": core,
            "action": "experiment",
        }
        resp = requests.post(url, headers=myobj)
        if resp.status_code != 200:
            print("Error fetching signed URLs: " + resp.text)
            sys.exit(1)
        return resp


# # end class def


AE_GLOBAL_API = "https://gyrfalcon.api.mips.com"


def __getChannelList(apikey):
    """
    Fetches the list of available channels for the given API key from the Atlas Explorer cloud API.

    Args:
        apikey (str): The API key used for authentication.

    Returns:
        dict: A dictionary containing the channel list under the 'channels' key. If the request fails or the API returns an error,
        returns a dictionary with an empty 'channels' list.

    Error Handling:
        - Prints an error message if the API returns a non-200 status code or if a request exception occurs.
        - Always returns a dictionary with a 'channels' key to prevent downstream IndexError.
    """
    global API_EXT_VERSION
    url = AE_GLOBAL_API + "/channellist"
    myobj = {"apikey": apikey, "extversion": API_EXT_VERSION}
    try:
        x = requests.get(url=url, headers=myobj)
        if x.status_code != 200:
            print(f"Error fetching channel list: {x.status_code} {x.text}")
            return {"channels": []}
        return x.json()
    except requests.RequestException as e:
        print(f"Exception during channel list fetch: {e}")
        return {"channels": []}


def __getUserValid(apikey):
    url = AE_GLOBAL_API + "/user"
    myobj = {"apikey": apikey}
    x = requests.get(url, headers=myobj)
    return x.status_code == 200


def configure(args):
    """Main program"""

    config = AtlasConfig(True, verbose=True)

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
        elif len(chnamellist) == 1:
            chanswer = chnamellist[0]
            print("Channel is automatically set to: " + chanswer)
        else:
            print("No channels are available for your API key. Please check your API key, API version, or contact support.")
            sys.exit(1)

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

        # Save to .env in project root
        env_path = os.path.join(os.getcwd(), ".env")
        env_line = f"MIPS_ATLAS_CONFIG={config['apikey']}:{config['channel']}:{config['region']}\n"
        try:
            with open(env_path, "w") as env_file:
                env_file.write(env_line)
            print(f".env file created/updated at {env_path} with your credentials.")
        except Exception as e:
            print(f"Warning: Could not write .env file: {e}")
    else:
        print("Invalid API Key")


def subcmd_configure(subparsers):
    parser = subparsers.add_parser(
        "configure",
        help="Configure Atlas Explorer Cloud Access",
    )
    parser.set_defaults(handler_function="configure")


if __name__ == "__main__":
    # Use the new secure CLI instead of the unsafe eval() pattern
    from .cli import AtlasExplorerCLI
    AtlasExplorerCLI.main()
