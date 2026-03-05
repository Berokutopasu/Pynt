#!/usr/bin/env pwsh
# Test script for Pynt endpoints

$BaseURL = "http://localhost:8000"
$Headers = @{"Content-Type" = "application/json"}

Write-Host "========================================"
Write-Host "Pynt Endpoints Test Suite"
Write-Host "========================================"
Write-Host ""

# Test 1: Health Check
Write-Host "[1/5] Testing Health Check..."
try {
    $response = Invoke-WebRequest -Uri "$BaseURL/health" -ErrorAction Stop -UseBasicParsing
    Write-Host "SUCCESS: Health check passed"
} catch {
    Write-Host "FAILED: $_"
}
Write-Host ""

# Test 2: Analyze Security
Write-Host "[2/5] Testing Analyze Security..."
$body2 = @{
    code = "import pickle`ndata = pickle.loads(user_input)"
    language = "python"
    filename = "test.py"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$BaseURL/analyze/security" -Method POST -Headers $Headers -Body $body2 -ErrorAction Stop -UseBasicParsing
    Write-Host "SUCCESS: Security analysis completed"
} catch {
    Write-Host "FAILED: $_"
}
Write-Host ""

# Test 3: Analyze Best Practices
Write-Host "[3/5] Testing Analyze Best Practices..."
$body3 = @{
    code = "def process_data(data):`n    return [item * 2 for item in data]"
    language = "python"
    filename = "test.py"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$BaseURL/analyze/best-practices" -Method POST -Headers $Headers -Body $body3 -ErrorAction Stop -UseBasicParsing
    Write-Host "SUCCESS: Best practices analysis completed"
} catch {
    Write-Host "FAILED: $_"
}
Write-Host ""

# Test 4: Analyze Fault
Write-Host "[4/5] Testing Analyze Fault..."
$body4 = @{
    code = "def divide(a, b):`n    return a / b"
    language = "python"
    filename = "test.py"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$BaseURL/analyze/fault-detection" -Method POST -Headers $Headers -Body $body4 -ErrorAction Stop -UseBasicParsing
    Write-Host "SUCCESS: Fault analysis completed"
} catch {
    Write-Host "FAILED: $_"
}
Write-Host ""

# Test 5: Analyze All
Write-Host "[5/5] Testing Analyze All (Parallel Analysis)..."
$body5 = @{
    code = "import os`npassword = os.environ.get('DB_PASSWORD')"
    language = "python"
    filename = "test.py"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$BaseURL/analyze/all" -Method POST -Headers $Headers -Body $body5 -ErrorAction Stop -UseBasicParsing
    Write-Host "SUCCESS: Parallel analysis completed"
} catch {
    Write-Host "FAILED: $_"
}
Write-Host ""

Write-Host "========================================"
Write-Host "Test Suite Complete"
Write-Host "========================================"
