
param([string] $xmlPath, [string] $testNames, [string] $imagePath)

class XMLWrapper {
    [xml] $xml

    XMLWrapper([String] $source_path) {
        $this.xml = [xml](Get-Content $source_path)
    }

    [void] AddBootTests([String] $testType, [String] $testName, [Array] $testParams) {
        $installSuiteTest = $this.xml.CreateElement('suiteTest')
        $installSuiteTest.AppendChild($this.xml.CreateTextNode("install_${testName}"))
        
        $bootSuiteTest = $this.xml.CreateElement('suiteTest')
        $bootSuiteTest.AppendChild($this.xml.CreateTextNode($testName))
        
        $installLisTest = [XMLWrapper]::GetInstallLisTest()
        $installLisTest.test.testName = "install_${testName}"

        $bootTest = [XMLWrapper]::GetKvpBasicTest()
        $bootTest.test.testName = $testName

        foreach($param in $testParams) {
            $paramElement = $installLisTest.CreateElement('param')
            $paramElement.AppendChild($installLisTest.CreateTextNode($param))
            $installLisTest.test.testParams.AppendChild($paramElement)
        }

        $this.xml.config.testSuites.suite.suiteTests.AppendChild($installSuiteTest)
        $this.xml.config.testSuites.suite.suiteTests.AppendChild($bootSuiteTest)
        $this.xml.config.testCases.AppendChild($this.xml.ImportNode($installLisTest.test, $true))
        $this.xml.config.testCases.AppendChild($this.xml.ImportNode($bootTest.test, $true))
    }

    [void] UpdateDistroImage([String] $imagePath) {
        $this.xml.config.global.imageStoreDir = $imagePath
    }

    [xml] static GetInstallLisTest() {
        return [xml]"
        <test>
            <files>remote-scripts/ica/install_lis_next.sh,remote-scripts/ica/utils.sh</files>
            <onError>Continue</onError>
            <setupScript>
                <file>setupscripts\RevertSnapshot.ps1</file>
                <file>Insfrastructure\patch-utils\copy-files.ps1</file>
            </setupScript>
            <testName>install_lis-next</testName>
            <testScript>install_lis_next.sh</testScript>
            <timeout>800</timeout>
            <testParams>
                <param>TC_COVERED=lis-next-01</param>
                <param>lis_cleanup=yes</param>
            </testParams>
        </test>
        "
    }

    [xml] static GetKvpBasicTest() {
        return [xml]"
        <test>
            <testName>KVP_Basic</testName>
            <testScript>SetupScripts\KVP_Basic.ps1</testScript>
            <timeout>600</timeout>
            <onError>Continue</onError>
            <noReboot>True</noReboot>
            <testparams>
                <param>TC_COVERED=KVP-01</param>
                <param>DE_change=no</param>
            </testparams>
        </test>
        "
    }

}


$xml = [XMLWrapper]::new($xmlPath)

$tests = $testNames.Split(';')
foreach($test in $tests) {
    $xml.AddBootTests('INSTALL_LIS_NEXT', $test, @("custom_lis_next=/root/${test}", "source_path=/root/builds/${test}"))
}

$xml.UpdateDistroImage($imagePath)
$xml.xml.Save($xmlPath)