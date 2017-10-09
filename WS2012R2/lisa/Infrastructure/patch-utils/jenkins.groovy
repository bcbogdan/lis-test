pipeline {
  agent any
  stages {
    stage('Search') { 
      steps {
        node ('UpstreamPatchesAgent'){
          script {
            timestamp = new java.text.SimpleDateFormat('MM-dd-yyyy-HH-mm-ss').format(new Date())
            currentBuild.displayName = "${timestamp}"
            patchFolderPath= "${params.PatchFolderPath}/${timestamp}"
            buildsPath = "${params.BuildsPath}/${timestamp}"
            failPath = "${params.FailPath}/${timestamp}"
          }           
          sh "echo '${params.FilesMap}' > /root/map.json"
          checkout([$class: 'GitSCM', branches: [[name: '*/patch-automation']], doGenerateSubmoduleConfigurations: false, extensions: [], gitTool: 'Default', submoduleCfg: [], userRemoteConfigs: [[url: 'https://github.com/bogdancarpusor/lis-test']]])
                    
          sh "python ./WS2012R2/lisa/Infrastructure/patch-utils/patch_utils.py create -d '${params.HistoryInterval}' -p ${patchFolderPath} -l ${params.LinuxRepoPath} -m /root/map.json"
          script {
            patches = sh (
                script: "ls ${patchFolderPath}",
                returnStdout: true).trim().split()
            currentBuild.description = "${patches.length} new patches"                            
            doApply = true
            if(patches.length == 0) {
                doApply = false
            }
          }    
        }
      }
    }
    stage('Apply') {
      steps {
        node ('UpstreamPatchesAgent') {
          script {
            if(doApply) {
              command = "python ./WS2012R2/lisa/Infrastructure/patch-utils/patch_utils.py apply ${patchFolderPath} -b ${buildsPath} -f ${failPath}"
              println(command)
              sh "${command}"
              //sh "python ./WS2012R2/lisa/Infrastructure/patch-utils/patch_utils.py apply '${patchFolderPath}' -b '${buildsPath}' -f '${failPath}'"
              builds = sh (
                script: "ls ${buildsPath}",
                returnStdout: true).trim().split()
              currentBuild.description += "\n builds.length applied"
              doCompile = true
              if(builds.length == 0) {
                doCompile = false 
              }
            } else {
              doCompile = false
              echo 'Skipped'
            }
          }
        }
      }
    }
    stage('Compile') { 
      steps {
        node ('UpstreamPatchesAgent'){
          script {
            if(doCompile) {
              sh "python ./WS2012R2/lisa/Infrastructure/patch-utils/patch_utils.py compile  ${buildsPath}"
              builds = sh (
                script: "ls ${buildsPath}",
                returnStdout: true).trim().split()
              currentBuild.description += "\n builds.length compiled"
              doBootTest = true
              patchNames = builds.join(';')
              if(builds.length == 0) {
                doBoottest = false 
              }
            } else {
              doBuildTest = false
              echo 'Skipped'
            }   
          }    
        }       
      }
    }
    stage('Boot') { 
      steps {
        script {
            // if(buildsCount > 0) {
            //     parallel (
            //         'RHEL70': {
            //             node('LIS-F2330') {
            //                 build job: 'Patch_Boot_Test', parameters: [string(name: 'PATCH_NAMES', value: "${patches}"), [$class: 'LabelParameterValue', name: 'node', label: 'LIS-F2329'], string(name: 'DISTRO_NAME', value: 'RHEL70')]
            //             }
            //         },    
            //         'RHEL71': {
            //             node('LIS-F2329') {
            //                 build job: 'Patch_Boot_Test', parameters: [string(name: 'PATCH_NAMES', value:  "${patches}"), [$class: 'LabelParameterValue', name: 'node', label: 'LIS-F2330'], string(name: 'DISTRO_NAME', value: 'RHEL72')]
                            
            //             }
                        
            //         },
            //         'RHEL74': {
            //             node('LIS-F2331') {
            //                 build job: 'Patch_Boot_Test', parameters: [string(name: 'PATCH_NAMES', value:  "${patches}"), [$class: 'LabelParameterValue', name: 'node', label: 'LIS-F2331'], string(name: 'DISTRO_NAME', value: 'RHEL71')]
            //             }
            //         },
            //         'Results': {
            //             node('UpstreamPatchesAgent') {
            //                 sh "python ./WS2012R2/lisa/Infrastructure/patch-utils/patch_utils.py serve 6"
            //             }
            //         }
            //     )
            // } else {
            //     echo 'Skipped'
            // }    
        }
        
    }          
    }
        stage('Commit') { 
                steps {
                    script {
                        parallel(
                            'Commit': {
                                node ('UpstreamPatchesAgent'){
                                    // buildsCount = sh (
                                    // script: "ls ${buildsPath}",
                                    // returnStdout: true).trim().split().length
                                    // if (buildsCount > 0) {
                                    //     def userInput = true
                                    //     def didTimeout = false
                                    //     try {
                                    //         timeout(time: 3, unit: 'HOURS') { 
                                    //             userInput = input(
                                    //             id: 'Proceed1', message: 'Commit new changes?', parameters: [
                                    //             [$class: 'BooleanParameterDefinition', defaultValue: true, description: '', name: 'Please confirm you agree with this']
                                    //             ])
                                    //         }
                                    //     } catch(err) {
                                    //         def user = err.getCauses()[0].getUser()
                                    //         if('SYSTEM' == user.toString()) {
                                    //             didTimeout = true
                                    //         } else {
                                    //             userInput = false
                                    //             echo "Aborted by: [${user}]"
                                    //         }
                                    //     }
                                        //sh "python ./WS2012R2/lisa/Infrastructure/patch-utils/patch_utils.py commit  ${params.BuildsPath} -e ${gitCredentials.email} -n ${gitCredentials.name} -p ${gitCredentials.password}"
                                
                                    // } else {
                                    //     echo 'No available patches to commit.'
                                    // }
                                }
                            },
                            'Other': {
                                node ('LIS-F2330') {
                                    
                                }
                            }
                        )
                    } 
                }
        }
    }
}