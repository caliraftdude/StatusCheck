#!/usr/bin/python
########################################################################################
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files(the "Software"), to deal in the Software 
# without restriction, including without l > imitation the rights to use, copy, modify, 
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
# permit persons to whom the Software is furnished to do so, subject to the following 
# conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
########################################################################################
# StatusCheck.py
#
# author:   Dan Holland
# date:     2020.02.13
# purpose:  
########################################################################################
import sys
import logging
import requests
from operator import itemgetter

# Handle annoying message everytime you connect to a bigip without a proper device certificate
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Determine the platform we are running on
from sys import platform
if platform == "linux" or platform == "linux2":
    PLATFORM = "linux"
elif platform == "darwin":
    PLATFORM = "linux"
elif platform == "win32":
    PLATFORM = "win32"



def main():

    try:
        processVirtuals()
        processPools()
        processDeviceMemory()
        processCPU()
        processDevPerf()
        processASM()
    except Exception as e:
        # Blanket - ugly catch all exception handler.  Likely, the issue is going to be catching accessint a bad dictionary atttribute,
        # and the code should do a better job of preparing/handling that inline - but to keep the complexity down I will just catch
        # all here and apologize accordingly
        print("Exception {}".format(e.args))

    return

def processVirtuals():
    topVirtuals = []

    # VIP Status
    response = requests.get('https://10.1.1.100/mgmt/tm/ltm/virtual', auth=('admin', 'admin'), verify=False).json()

    for virtual in response['items']:
        # List to store the name and connections stats for this vip
        vstatItem = []
        
        # Get the status object for a virtual from the F5 and output the status
        status = requests.get('https://10.1.1.100/mgmt/tm/ltm/virtual/'+ virtual['name'] + '/stats', auth=('admin', 'admin'), verify=False).json()
        outputVSStats('Virtual Server', status, ['tmName', 'status.enabledState', 'status.availabilityState', 'status.statusReason'])

        # Get the stats node and extract the connection stats 
        stats = getStatsNode(status)
        vstatItem.append(virtual['name'])
        vstatItem.append(stats['clientside.curConns']['value'])
        vstatItem.append(stats['clientside.maxConns']['value'])
        vstatItem.append(stats['clientside.totConns']['value'])

        # Append the topVirtuals list with the connection count list for this virtual
        topVirtuals.append(vstatItem)

    # pass the virtuals list and process the Top 10
    processTopVirtuals(topVirtuals)
    return

def processTopVirtuals(topVirtuals):
    # Sort the topVirtuals on curConnections stats and truncate to the top 10
    sorted(topVirtuals, key=itemgetter(1) )
    del topVirtuals[10:]

    # print out the top 10
    print("Top 10 virtuals by connection count")
    for tv in topVirtuals:
        print(tv[0])

    # Line feed
    print("\n")

    return


def processPools():
    # Pool Status
    pools = requests.get('https://10.1.1.100/mgmt/tm/ltm/pool/', auth=('admin', 'admin'), verify=False).json()

    for pool in pools['items']:
        selflink = (pool['selfLink'].split('?',1)[0] + '/stats/').replace('localhost', '10.1.1.100')
        memberlink = (pool['membersReference']['link'].split('?',1)[0] ).replace('localhost', '10.1.1.100')

        pool_stats = requests.get(selflink, auth=('admin', 'admin'), verify=False).json()
        outputVSStats('Pool', pool_stats, ['tmName', 'status.enabledState', 'status.availabilityState', 'status.statusReason'])

        members = requests.get(memberlink, auth=('admin', 'admin'), verify=False).json()
        
        for member in members['items']:
            selflink = (member['selfLink'].split('?',1)[0] + '/stats/').replace('localhost', '10.1.1.100')
            member_stats = requests.get(selflink, auth=('admin', 'admin'), verify=False).json()

            outputVSStats('Pool Member', member_stats, ['nodeName', 'status.enabledState', 'status.availabilityState', 'status.statusReason'])

def processDeviceMemory():
    # Device Memory
    devMemory = requests.get('https://10.1.1.100/mgmt/tm/sys/memory/', auth=('admin', 'admin'), verify=False).json()
    devMemory = devMemory['entries']['https://localhost/mgmt/tm/sys/memory/memory-host']['nestedStats']['entries']['https://localhost/mgmt/tm/sys/memory/memory-host/0']['nestedStats']['entries']

    for key in list(devMemory.keys()):
        if key == 'hostId':
            print(key + ':\t' + devMemory[key]['description'])
            continue
        
        print('\t' + key + ':\t\t{}'.format(devMemory[key]['value']))

def processCPU():
    # Device CPU
    devCPU = requests.get('https://10.1.1.100/mgmt/tm/sys/cpu', auth=('admin', 'admin'), verify=False).json()
    devCPU = devCPU['entries']['https://localhost/mgmt/tm/sys/cpu/0']['nestedStats']['entries']['https://localhost/mgmt/tm/sys/cpu/0/cpuInfo']['nestedStats']['entries']
    stats = ['fiveSecAvgSystem', 'oneMinAvgSystem', 'fiveMinAvgSystem']

    for entry in list(devCPU.keys()):
        cpu = devCPU[entry]['nestedStats']['entries']

        print('cpuID: {}'.format(cpu['cpuId']['value']))
        for item in stats:
            print('\t' + item + '\t{}'.format(cpu[item]['value']))

def processDevPerf():
    # Device Performance
    devPerf = requests.get('https://10.1.1.100/mgmt/tm/sys/performance/throughput/', auth=('admin', 'admin'), verify=False).json()

    for key in list(devPerf['entries'].keys()):
        print('\n')
        entry = devPerf['entries'][key]
        for item in (list(entry['nestedStats']['entries'].keys())):
            print(item + ':\t{}'.format(entry['nestedStats']['entries'][item]['description']))

def processASM():
    # ASM Stats
    asmPolicies = requests.get('https://10.1.1.100/mgmt/tm/asm/policies', auth=('admin', 'admin'), verify=False).json()
    
    for policy in asmPolicies['items']:
        print(policy['name'])
        print('\tID:\t'+policy['id'])
        print('\tEnforcement Mode:\t'+policy['enforcementMode'])
        print('\tAttached VS:')
        for vs in policy['virtualServers']:
            print('\t\t'+vs)

    return

#################################################################
#   Misc utility Functions
#################################################################
def getLogging():
    # Returns a logging objectfor the system and formats it
    FORMAT = '%(asctime)-15s %(levelname)s\tFunc: %(funcName)s():\t%(message)s'
    #FORMAT = '%(message)s'
    logging.basicConfig(format=FORMAT)
    return logging.getLogger('f5-StatusCheck')

def check_ping(address):
    # Check ping and deal with the fact that linux and windows do have different cmd line arguments that clash
    global PLATFORM

    if PLATFORM == "linux":
        response = os.system("ping -c 1 " + address)
    elif PLATFORM =="win32":
        response = os.system("ping -n 1 " + address)
    else:
        log.exception("Unsupported platform, exiting...")
        sys.exit(-1)

    if response == 0:
        return True

    return False  

def getStatsNode(obj):
    # Stats are kept, for whatever insane reason, within a dict of a dict of a dict, of a dict...etc.. and one of which the keys are unknown.  This is a hack
    # to get that 'name' so we can then reduce this nonsense t just accessing a single dictionary.  lame.
    key = list( obj['entries'].keys() )[0]
    return obj['entries'][key]['nestedStats']['entries']

def outputVSStats(type, obj, attrlist):
    # Type: The type of object that you are printing (VS, Pool, etc..) - string
    # obj : The mgmt/REST node object.  This is *SPECIFIC* to the VS tree... a better general routine could be built
    # attrlist: A list of the attributes that you want to print out for that node
    stats = getStatsNode(obj)

    # Print out the type without indentation, then the list of attributes with indentation
    print("Type:\t{}".format(type))
    for attr in attrlist:
        print("\t" + attr + "\t{}".format(stats[attr]['description']) )

    # Line feed to space out each object
    print("\n")
    return

#################################################################
#   Entry point
#################################################################
if __name__ == "__main__":
    # Get logging object
    log = getLogging()
    log.setLevel(logging.ERROR)

    main()

    # Note - This could be improved a lot and also handle, at a minumum, these responses intelligently.  However,
    # this isn't inteded to be production-worthy code and more an exercise in how to get this content from a box
    # Also, supporting getopts and providing a means to output a file or even better CSV would be preferable

    #200 – OK. The request was successful. The answer itself depends on the method used (GET, POST, etc.) and the API specification.
    #204 – No Content. The server successfully processed the request and did not return any content.
    #301 – Moved Permanently. The server responds that the requested page (endpoint) has been moved to another address and redirects to this address.
    #400 – Bad Request. The server cannot process the request because the client-side errors (incorrect request format).
    #401 – Unauthorized. Occurs when authentication was failed, due to incorrect credentials or even their absence.
    #403 – Forbidden. Access to the specified resource is denied.
    #404 – Not Found. The requested resource was not found on the server.
    #500 – Internal Server Error. Occurs when an unknown error has occurred on the server.