# ======================================
# UNIVERSAL SECURITY CHECK
# Python + Java Spring Boot + Docker
# ======================================

$ErrorActionPreference = "Continue"

$SecurityFailed = $false

Write-Host ""
Write-Host "======================================"
Write-Host " UNIVERSAL SECURITY CHECK"
Write-Host "======================================"
Write-Host ""

# ======================================
# PROJECT DETECTION
# ======================================

Write-Host "[INFO] Detecting project type..."
Write-Host ""

$IsPython = $false
$IsJava = $false
$HasDockerfile = $false

# ---------- Python Detection ----------

$PythonFiles = @(
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "setup.py",
    "setup.cfg"
)

foreach ($File in $PythonFiles) {

    if (Test-Path $File) {
        $IsPython = $true
    }
}

if (Get-ChildItem -Path . -Filter "*.py" -Recurse -ErrorAction SilentlyContinue) {
    $IsPython = $true
}

# ---------- Java Detection ----------

if (
    (Test-Path "pom.xml") -or
    (Test-Path "build.gradle") -or
    (Test-Path "build.gradle.kts")
) {
    $IsJava = $true
}

# ---------- Docker Detection ----------

if (Test-Path "Dockerfile") {
    $HasDockerfile = $true
}

if ($IsPython) {
    Write-Host "[INFO] Python project detected."
}

if ($IsJava) {
    Write-Host "[INFO] Java project detected."
}

if ($HasDockerfile) {
    Write-Host "[INFO] Dockerfile detected."
}

if (
    (-not $IsPython) -and
    (-not $IsJava) -and
    (-not $HasDockerfile)
) {

    Write-Host ""
    Write-Host "[FAIL] No supported project type detected."
    exit 1
}

Write-Host ""

# ======================================
# 1. GITLEAKS - SECRET SCANNING
# ======================================

Write-Host "======================================"
Write-Host "[1/8] GITLEAKS SECRET SCAN"
Write-Host "======================================"
Write-Host ""

Write-Host "[INFO] Scanning repository for secrets..."
Write-Host ""

gitleaks dir . --redact --exit-code 1

$GitleaksExitCode = $LASTEXITCODE

if ($GitleaksExitCode -ne 0) {

    Write-Host ""
    Write-Host "[FAIL] Gitleaks detected secrets."
    $SecurityFailed = $true

}
else {

    Write-Host ""
    Write-Host "[PASS] No secrets detected by Gitleaks."

}

# ======================================
# 2. SEMGREP - SAST
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host "[2/8] SEMGREP SAST"
Write-Host "======================================"
Write-Host ""

# ---------- Python ----------

if ($IsPython) {

    Write-Host "[INFO] Running Semgrep Python security rules..."
    Write-Host ""

    semgrep scan --config p/python --error .

    $SemgrepPythonExitCode = $LASTEXITCODE

    if ($SemgrepPythonExitCode -ne 0) {

        Write-Host ""
        Write-Host "[FAIL] Semgrep detected Python security issues."
        $SecurityFailed = $true

    }
    else {

        Write-Host ""
        Write-Host "[PASS] Python Semgrep scan passed."

    }
}

# ---------- Java ----------

if ($IsJava) {

    Write-Host "[INFO] Running Semgrep Java security rules..."
    Write-Host ""

    semgrep scan --config p/java --error .

    $SemgrepJavaExitCode = $LASTEXITCODE

    if ($SemgrepJavaExitCode -ne 0) {

        Write-Host ""
        Write-Host "[FAIL] Semgrep detected Java security issues."
        $SecurityFailed = $true

    }
    else {

        Write-Host ""
        Write-Host "[PASS] Java Semgrep scan passed."

    }
}

if ((-not $IsPython) -and (-not $IsJava)) {

    Write-Host "[INFO] Semgrep skipped - no Python/Java project detected."

}

# ======================================
# 3. TRIVY FILESYSTEM SCAN
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host "[3/8] TRIVY FILESYSTEM SCAN"
Write-Host "======================================"
Write-Host ""

Write-Host "[INFO] Scanning project filesystem..."
Write-Host ""

trivy fs `
    --severity HIGH,CRITICAL `
    --exit-code 1 `
    .

$TrivyFsExitCode = $LASTEXITCODE

if ($TrivyFsExitCode -ne 0) {

    Write-Host ""
    Write-Host "[FAIL] Trivy filesystem scan detected HIGH/CRITICAL vulnerabilities."
    $SecurityFailed = $true

}
else {

    Write-Host ""
    Write-Host "[PASS] Trivy filesystem scan completed."

}

# ======================================
# 4. DEPENDENCY SECURITY
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host "[4/8] DEPENDENCY SECURITY"
Write-Host "======================================"
Write-Host ""

# ---------- Python pip-audit ----------

if ($IsPython) {

    if (Test-Path "requirements.txt") {

        Write-Host "[INFO] Running pip-audit..."
        Write-Host ""

        pip-audit -r requirements.txt

        $PipAuditExitCode = $LASTEXITCODE

        if ($PipAuditExitCode -ne 0) {

            Write-Host ""
            Write-Host "[FAIL] pip-audit detected vulnerable Python dependencies."
            $SecurityFailed = $true

        }
        else {

            Write-Host ""
            Write-Host "[PASS] Python dependency audit passed."

        }

    }
    else {

        Write-Host "[INFO] requirements.txt not found."
        Write-Host "[INFO] pip-audit skipped."

    }
}

# ---------- Java Dependency Check ----------

if ($IsJava) {

    Write-Host "[INFO] Java dependency security scan:"
    Write-Host "[INFO] OWASP Dependency-Check is currently skipped."
    Write-Host "[INFO] NVD API key configuration will be added later."

}

if ((-not $IsPython) -and (-not $IsJava)) {

    Write-Host "[INFO] Dependency security skipped."

}

# ======================================
# 5. APPLICATION TESTS
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host "[5/8] APPLICATION TESTS"
Write-Host "======================================"
Write-Host ""

# ---------- Python Tests ----------

if ($IsPython) {

    $PythonTests = Get-ChildItem `
        -Path . `
        -Recurse `
        -File `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "test_*.py" -or
            $_.Name -like "*_test.py"
        }

    if ($PythonTests) {

        Write-Host "[INFO] Python tests detected."
        Write-Host "[INFO] Running pytest..."
        Write-Host ""

        pytest

        $PytestExitCode = $LASTEXITCODE

        if ($PytestExitCode -ne 0) {

            Write-Host ""
            Write-Host "[FAIL] Python tests failed."
            $SecurityFailed = $true

        }
        else {

            Write-Host ""
            Write-Host "[PASS] Python tests passed."

        }

    }
    else {

        Write-Host "[INFO] No Python tests detected."
        Write-Host "[INFO] pytest skipped."

    }
}

# ---------- Java Tests ----------

if ($IsJava) {

    if (Test-Path "pom.xml") {

        Write-Host "[INFO] Maven project detected."
        Write-Host "[INFO] Running Maven tests..."
        Write-Host ""

        mvn clean test

        $MavenExitCode = $LASTEXITCODE

        if ($MavenExitCode -ne 0) {

            Write-Host ""
            Write-Host "[FAIL] Maven tests failed."
            $SecurityFailed = $true

        }
        else {

            Write-Host ""
            Write-Host "[PASS] Maven tests passed."

        }

    }
    elseif (
        (Test-Path "build.gradle") -or
        (Test-Path "build.gradle.kts")
    ) {

        Write-Host "[INFO] Gradle project detected."
        Write-Host "[INFO] Gradle test execution will be added later."

    }
}

if ((-not $IsPython) -and (-not $IsJava)) {

    Write-Host "[INFO] Application tests skipped."

}

# ======================================
# 6. DOCKER SECURITY
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host "[6/8] DOCKER SECURITY"
Write-Host "======================================"
Write-Host ""

$ImageName = "universal-security-test:security-check"
$DockerBuildExitCode = 1
$TrivyImageExitCode = 1

if ($HasDockerfile) {

    # ----------------------------------
    # 6.1 Dockerfile Configuration Scan
    # ----------------------------------

    Write-Host "[6.1] Trivy Dockerfile configuration scan..."
    Write-Host ""

    trivy config `
        --severity HIGH,CRITICAL `
        --exit-code 1 `
        .

    $TrivyConfigExitCode = $LASTEXITCODE

    if ($TrivyConfigExitCode -ne 0) {

        Write-Host ""
        Write-Host "[FAIL] Dockerfile configuration issues detected."
        $SecurityFailed = $true

    }
    else {

        Write-Host ""
        Write-Host "[PASS] Dockerfile configuration scan passed."

    }

    # ----------------------------------
    # 6.2 Docker Build
    # ----------------------------------

    Write-Host ""
    Write-Host "[6.2] Building Docker image..."
    Write-Host ""

    docker build `
        --load `
        -t $ImageName `
        .

    $DockerBuildExitCode = $LASTEXITCODE

    if ($DockerBuildExitCode -ne 0) {

        Write-Host ""
        Write-Host "[FAIL] Docker image build failed."
        $SecurityFailed = $true

    }
    else {

        Write-Host ""
        Write-Host "[PASS] Docker image built successfully."
        Write-Host "[INFO] Image: $ImageName"

    }

    # ----------------------------------
    # 6.3 Container Image Vulnerability
    # ----------------------------------

    if ($DockerBuildExitCode -eq 0) {

        Write-Host ""
        Write-Host "[6.3] Trivy container image scan..."
        Write-Host ""

        trivy image `
            --severity HIGH,CRITICAL `
            --exit-code 1 `
            $ImageName

        $TrivyImageExitCode = $LASTEXITCODE

        if ($TrivyImageExitCode -ne 0) {

            Write-Host ""
            Write-Host "[FAIL] Container image contains HIGH/CRITICAL vulnerabilities."
            $SecurityFailed = $true

        }
        else {

            Write-Host ""
            Write-Host "[PASS] Container image vulnerability scan passed."

        }

    }
    else {

        Write-Host ""
        Write-Host "[INFO] Image vulnerability scan skipped because Docker build failed."

    }

}
else {

    Write-Host "[INFO] Dockerfile not found."
    Write-Host "[INFO] Docker security checks skipped."

}

# ======================================
# 7. SBOM GENERATION
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host "[7/8] SBOM GENERATION"
Write-Host "======================================"
Write-Host ""

if ($DockerBuildExitCode -eq 0) {

    Write-Host "[INFO] Generating CycloneDX SBOM..."
    Write-Host ""

    $SBOMFile = Join-Path $PWD "sbom.json"

    trivy image `
        --format cyclonedx `
        --output $SBOMFile `
        $ImageName

    $SBOMExitCode = $LASTEXITCODE

    if ($SBOMExitCode -ne 0) {

        Write-Host ""
        Write-Host "[FAIL] SBOM generation failed."
        $SecurityFailed = $true

    }
    else {

        if (Test-Path $SBOMFile) {

            Write-Host ""
            Write-Host "[PASS] SBOM generated successfully."
            Write-Host "[INFO] SBOM file: $SBOMFile"

        }
        else {

            Write-Host ""
            Write-Host "[FAIL] SBOM command completed but sbom.json was not created."
            $SecurityFailed = $true

        }

    }

}
else {

    Write-Host "[INFO] SBOM generation skipped because Docker image build failed."

}

# ======================================
# 8. OWASP ZAP DAST
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host "[8/8] OWASP ZAP DAST"
Write-Host "======================================"
Write-Host ""

$ZapImage = "ghcr.io/zaproxy/zaproxy:stable"
$ZapConfig = Join-Path $PWD "zap-config.yaml"
$ZapReport = Join-Path $PWD "zap-policy-report.json"

if (-not (Test-Path $ZapConfig)) {

    Write-Host "[INFO] ZAP configuration not found."
    Write-Host "[INFO] ZAP DAST skipped."

}
else {

    Write-Host "[INFO] Starting OWASP ZAP DAST..."
    Write-Host ""

    docker run --rm `
        -v "${PWD}:/zap/wrk/:rw" `
        $ZapImage `
        zap.sh -cmd `
        -autorun /zap/wrk/zap-config.yaml

    $ZapExitCode = $LASTEXITCODE

    if ($ZapExitCode -ne 0) {

        Write-Host ""
        Write-Host "[FAIL] ZAP scan execution failed."
        Write-Host "[INFO] ZAP exit code: $ZapExitCode"

        $SecurityFailed = $true

    }
    elseif (-not (Test-Path $ZapReport)) {

        Write-Host ""
        Write-Host "[FAIL] ZAP scan completed but JSON report was not created."

        $SecurityFailed = $true

    }
    else {

        Write-Host ""
        Write-Host "[PASS] ZAP scan completed."
        Write-Host "[INFO] ZAP report: $ZapReport"
        Write-Host ""

        # ----------------------------------
        # 8.1 ZAP Security Policy
        # ----------------------------------

        Write-Host "[INFO] Applying ZAP security policy..."
        Write-Host "[INFO] Medium, High and Critical findings will BLOCK deployment."
        Write-Host ""

        try {

            $ZapReportData = Get-Content $ZapReport -Raw |
                ConvertFrom-Json

            $BlockingAlerts = @(
                $ZapReportData.site.alerts |
                    Where-Object {
                        [int]$_.riskcode -ge 2
                    }
            )

            if ($BlockingAlerts.Count -gt 0) {

                Write-Host ""
                Write-Host "======================================"
                Write-Host " ZAP SECURITY GATE: FAILED"
                Write-Host "======================================"
                Write-Host ""

                Write-Host "[FAIL] Blocking ZAP findings detected:"
                Write-Host ""

                $BlockingAlerts |
                    Select-Object `
                        riskcode,
                        riskdesc,
                        alert,
                        confidence |
                    Format-Table -AutoSize

                $SecurityFailed = $true

            }
            else {

                Write-Host ""
                Write-Host "======================================"
                Write-Host " ZAP SECURITY GATE: PASSED"
                Write-Host "======================================"
                Write-Host ""

                Write-Host "[PASS] No Medium/High/Critical ZAP findings detected."

            }

        }
        catch {

            Write-Host ""
            Write-Host "[FAIL] Unable to parse ZAP JSON report."
            Write-Host $_.Exception.Message

            $SecurityFailed = $true

        }

    }

}

# ======================================
# FINAL SECURITY GATE
# ======================================

Write-Host ""
Write-Host "======================================"
Write-Host " FINAL SECURITY GATE"
Write-Host "======================================"
Write-Host ""

if ($SecurityFailed) {

    Write-Host "======================================"
    Write-Host " SECURITY CHECK: FAILED"
    Write-Host "======================================"
    Write-Host ""

    Write-Host "[FAIL] One or more security checks failed."
    Write-Host "[BLOCKED] DEPLOYMENT BLOCKED."
    Write-Host ""

    exit 1

}
else {

    Write-Host "======================================"
    Write-Host " SECURITY CHECK: PASSED"
    Write-Host "======================================"
    Write-Host ""

    Write-Host "[PASS] All configured security checks passed."
    Write-Host "[ALLOWED] DEPLOYMENT ALLOWED."
    Write-Host ""

    exit 0

}