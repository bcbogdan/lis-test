
param([string] $xmlPath, [string] $testNames, [string] $distroName, [string] $propertiesPath)

class XMLWrapper {
    [xml] $xml
    [System.Collections.Hashtable] $properties

    XMLWrapper([String] $source_path, [String] $propertiesFile) {
        $this.xml = [xml](Get-Content $source_path)
        $this.properties =  Convertfrom-Stringdata (Get-Content $propertiesFile -raw)
    }

    [void] AddTest([String] $testType, [String] $testName, [Array] $testParams) {
        $suiteTest = $this.xml.CreateElement('suiteTest')
        $suiteTest.AppendChild($this.xml.CreateTextNode($testName))

        $testDescription = $this.getTestDescription($testType)
        $testDescription.test.testName = $testName

        foreach($param in $testParams) {
            $paramElement = $testDescription.CreateElement('param')
            $paramElement.AppendChild($testDescription.CreateTextNode($param))
            $testDescription.test.testParams.AppendChild($paramElement)
        }

        $this.xml.config.testSuites.suite.suiteTests.AppendChild($suiteTest)
        $this.xml.config.testCases.AppendChild($this.xml.ImportNode($testDescription.test, $true))
    }

    [void] UpdateDistroImage([String] $distroName) {
        $imagePath = $this.properties."${distroName}"
        $this.xml.config.global.imageStoreDir = $imagePath
    }

    [xml] getTestDescription([String] $testType) {
        #TODO: Add multiple test descriptions

        return [xml]"
        <test>
                <files>remote-scripts/ica/install_lis_next.sh,remote-scripts/ica/utils.sh</files>
                <onError>Abort</onError>
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

}


$xml = [XMLWrapper]::new($xmlPath, $propertiesPath)

$tests = $testNames.Split(';')
foreach($test in $tests) {
    $xml.AddTest('INSTALL_LIS_NEXT', $test, @("custom_lis_next=/root/${test}"))
}

$xml.UpdateDistroImage($distroName)
$xml.xml.Save($xmlPath)