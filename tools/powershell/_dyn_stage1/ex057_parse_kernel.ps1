$targetPids = @('16640', '9276')
$settings = New-Object System.Xml.XmlReaderSettings
$settings.IgnoreWhitespace = $true
$reader = [System.Xml.XmlReader]::Create('Y:\ex057_kernel.xml', $settings)
$results = New-Object System.Collections.Generic.List[object]

while ($reader.Read()) {
    if ($reader.NodeType -ne [System.Xml.XmlNodeType]::Element -or $reader.LocalName -ne 'Event') {
        continue
    }

    $subtree = $reader.ReadSubtree()
    $doc = New-Object System.Xml.XmlDocument
    $doc.Load($subtree)
    $subtree.Close()

    $system = $doc.SelectSingleNode("//*[local-name()='System']")
    $execution = $doc.SelectSingleNode("//*[local-name()='Execution']")
    $eventData = $doc.SelectSingleNode("//*[local-name()='EventData']")
    $rendering = $doc.SelectSingleNode("//*[local-name()='RenderingInfo']")
    if ($null -eq $system -or $null -eq $execution -or $null -eq $eventData) {
        continue
    }

    $data = @{}
    foreach ($node in $eventData.ChildNodes) {
        if ($node.LocalName -eq 'Data') {
            $data[$node.GetAttribute('Name')] = $node.InnerText
        }
    }

    $processId = $data['ProcessId']
    if ($null -eq $processId) {
        $processId = $execution.GetAttribute('ProcessID')
    }
    $processId = $processId.Trim()
    if ($targetPids -notcontains $processId) {
        continue
    }

    $fileName = $data['FileName']
    $eventName = if ($rendering) { $rendering.SelectSingleNode("*[local-name()='EventName']").InnerText } else { '' }
    if ($fileName -and $fileName -match 'EX035_DIR') {
        $results.Add([PSCustomObject]@{
            Time = $system.SelectSingleNode("*[local-name()='TimeCreated']").GetAttribute('SystemTime')
            ProcessId = $processId
            Opcode = $system.SelectSingleNode("*[local-name()='Opcode']").InnerText
            Event = $eventName
            File = $fileName
        })
    }
}

$reader.Close()
$results | Sort-Object Time | Select-Object Time, Opcode, Event, File | Format-List
"COUNT=$($results.Count)"
