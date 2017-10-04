########################################################################
#
# Linux on Hyper-V and Azure Test Code, ver. 1.0.0
# Copyright (c) Microsoft Corporation
#
# All rights reserved.
# Licensed under the Apache License, Version 2.0 (the ""License"");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION
# ANY IMPLIED WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR
# PURPOSE, MERCHANTABLITY OR NON-INFRINGEMENT.
#
# See the Apache Version 2.0 License for specific language governing
# permissions and limitations under the License.
#
########################################################################


param([string] $vmName, [string] $hvServer, [string] $testParams)

#
# Check input arguments
#
if (-not $vmName)
{
    "Error: VM name is null"
    return $retVal
}

if (-not $hvServer)
{
    "Error: hvServer is null"
    return $retVal
}

if (-not $testParams)
{
    "Error: No testParams provided"
    "       This script requires the snapshot name as the test parameter"
    return $retVal
}

$params = $testParams.Split(";")
foreach ($p in $params)
{
    $fields = $p.Split("=")
        switch -wildcard ($fields[0].Trim())
        {
        "custom_lis_next"    { $snapshot = $fields[1].Trim() }
        "source_address"     { $revert_vms = $fields[1].Trim() }
        "sshKey"             { $sshKey  = $fields[1].Trim() }
        "ipv4"               { $ipv4    = $fields[1].Trim() }
        "SSH_PRIVATE_KEY"    { $privateKey    = $fields[1].Trim() }
        "REMOTE_USER"               { $remoteUser    = $fields[1].Trim() }
        default  {}
        }
}


$copyCmd = "scp -r -i .ssh/${privateKey} -o StrictHostKeyChecking=no ${remoteUser}@${source_address}:${source_path} ${custom_lis_next}"
Start-Process bin\plink -ArgumentList "-i ssh\${sshKey} root@${ipv4} ${copyCmd}" -NoNewWindow

