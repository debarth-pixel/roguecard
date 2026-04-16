Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$projectRoot = Split-Path -Parent $PSScriptRoot
$outputRoot = Join-Path $projectRoot "assets\\ui\\character_select"

$artExports = @(
    @{
        Input = Join-Path $projectRoot "arts\\enforcer_selected.png"
        Output = Join-Path $outputRoot "enforcer_selected_cutout.png"
        Threshold = 12.0
    },
    @{
        Input = Join-Path $projectRoot "arts\\controller_selected.png"
        Output = Join-Path $outputRoot "controller_selected_cutout.png"
        Threshold = 18.0
    }
)

function Get-ColorDistance {
    param(
        [System.Drawing.Color]$Left,
        [System.Drawing.Color]$Right
    )

    $dr = [double]($Left.R - $Right.R)
    $dg = [double]($Left.G - $Right.G)
    $db = [double]($Left.B - $Right.B)
    return [math]::Sqrt(($dr * $dr) + ($dg * $dg) + ($db * $db))
}

function Add-Seed {
    param(
        [int]$X,
        [int]$Y,
        [int]$Width,
        [bool[]]$Visited,
        [bool[]]$Background,
        [System.Collections.Generic.Queue[int]]$Queue
    )

    $index = ($Y * $Width) + $X
    if ($Visited[$index]) {
        return
    }
    $Visited[$index] = $true
    $Background[$index] = $true
    $Queue.Enqueue($index)
}

function Export-CharacterCutout {
    param(
        [string]$InputPath,
        [string]$OutputPath,
        [double]$Threshold
    )

    $bitmap = [System.Drawing.Bitmap]::new($InputPath)
    try {
        $width = $bitmap.Width
        $height = $bitmap.Height
        $visited = New-Object bool[] ($width * $height)
        $background = New-Object bool[] ($width * $height)
        $queue = [System.Collections.Generic.Queue[int]]::new()

        for ($x = 0; $x -lt $width; $x++) {
            Add-Seed -X $x -Y 0 -Width $width -Visited $visited -Background $background -Queue $queue
            Add-Seed -X $x -Y ($height - 1) -Width $width -Visited $visited -Background $background -Queue $queue
        }

        for ($y = 0; $y -lt $height; $y++) {
            Add-Seed -X 0 -Y $y -Width $width -Visited $visited -Background $background -Queue $queue
            Add-Seed -X ($width - 1) -Y $y -Width $width -Visited $visited -Background $background -Queue $queue
        }

        while ($queue.Count -gt 0) {
            $index = $queue.Dequeue()
            $x = $index % $width
            $y = [int][math]::Floor($index / $width)
            $current = $bitmap.GetPixel($x, $y)

            foreach ($offset in @(
                @(-1, 0),
                @(1, 0),
                @(0, -1),
                @(0, 1)
            )) {
                $nextX = $x + $offset[0]
                $nextY = $y + $offset[1]
                if ($nextX -lt 0 -or $nextX -ge $width -or $nextY -lt 0 -or $nextY -ge $height) {
                    continue
                }
                $nextIndex = ($nextY * $width) + $nextX
                if ($visited[$nextIndex]) {
                    continue
                }

                $candidate = $bitmap.GetPixel($nextX, $nextY)
                $visited[$nextIndex] = $true

                if ($candidate.A -eq 0) {
                    $background[$nextIndex] = $true
                    $queue.Enqueue($nextIndex)
                    continue
                }

                $distance = Get-ColorDistance -Left $current -Right $candidate
                if ($distance -le $Threshold) {
                    $background[$nextIndex] = $true
                    $queue.Enqueue($nextIndex)
                }
            }
        }

        $result = New-Object System.Drawing.Bitmap($width, $height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            for ($y = 0; $y -lt $height; $y++) {
                for ($x = 0; $x -lt $width; $x++) {
                    $index = ($y * $width) + $x
                    $pixel = $bitmap.GetPixel($x, $y)
                    if ($background[$index]) {
                        $result.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(0, $pixel.R, $pixel.G, $pixel.B))
                    }
                    else {
                        $result.SetPixel($x, $y, $pixel)
                    }
                }
            }

            $outputDir = Split-Path -Parent $OutputPath
            if (-not (Test-Path -LiteralPath $outputDir)) {
                New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
            }
            $result.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        }
        finally {
            $result.Dispose()
        }
    }
    finally {
        $bitmap.Dispose()
    }
}

$written = @()
foreach ($export in $artExports) {
    Export-CharacterCutout -InputPath $export.Input -OutputPath $export.Output -Threshold $export.Threshold
    $written += $export.Output
}

$written
