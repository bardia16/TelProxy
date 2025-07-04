#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

VALIDATION_SERVER="http://127.0.0.1:9100"

echo -e "${BLUE}Testing Connection to Validation Server${NC}\n"

# Test 1: Basic connectivity test
echo -e "${BLUE}Test 1: Testing Basic Connectivity${NC}"
if curl -s --connect-timeout 5 "${VALIDATION_SERVER}/" -o /dev/null; then
    echo -e "${GREEN}✓ Can reach validation server${NC}"
else
    echo -e "${RED}✗ Cannot reach validation server${NC}"
fi
echo -e "\n"

# Test 2: API Response Test
echo -e "${BLUE}Test 2: Testing API Response${NC}"
RESPONSE=$(curl -v -s -X POST "${VALIDATION_SERVER}/validate" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}" \
  -d '{
    "proxy": "8.8.8.8:80",
    "proxy_type": "http",
    "ping_count": 1,
    "ping_delay": 0.1
  }' 2>&1)

HTTP_STATUS=$(echo "$RESPONSE" | grep "Status:" | cut -d' ' -f2)
RESPONSE_BODY=$(echo "$RESPONSE" | grep -v "Status:" | grep -v "^*" | grep -v "^>" | grep -v "^<")

echo -e "Full response details:"
echo "$RESPONSE"
echo -e "\nStatus code: ${HTTP_STATUS}"

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ API is responding correctly${NC}"
else
    echo -e "${RED}✗ API returned status ${HTTP_STATUS}${NC}"
fi

echo -e "\nTrying to parse response as JSON:"
if [ ! -z "$RESPONSE_BODY" ]; then
    if echo "$RESPONSE_BODY" | python3 -m json.tool > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Response is valid JSON${NC}"
        echo "Formatted response:"
        echo "$RESPONSE_BODY" | python3 -m json.tool
    else
        echo -e "${RED}✗ Response is not valid JSON${NC}"
        echo "Raw response body:"
        echo "$RESPONSE_BODY"
    fi
else
    echo -e "${RED}✗ Response body is empty${NC}"
fi
echo -e "\n"

# Test 3: Testing with real proxy from your system
echo -e "${BLUE}Test 3: Testing with Current Working Proxy${NC}"
# Get first working proxy from your database or config
PROXY="103.155.217.52:41485"  # Replace this with an actual working proxy
curl -s -X POST "${VALIDATION_SERVER}/validate" \
  -H "Content-Type: application/json" \
  -d "{
    \"proxy\": \"${PROXY}\",
    \"proxy_type\": \"http\",
    \"ping_count\": 3
  }" | python3 -m json.tool 2>/dev/null || echo "Failed to parse response as JSON"
echo -e "\n"

# Test 4: MTProto Test (Telegram Connectivity)
echo -e "${BLUE}Test 4: Testing MTProto Validation${NC}"
curl -s -X POST "${VALIDATION_SERVER}/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "proxy": "1.1.1.1:443",
    "proxy_type": "mtproto",
    "ping_count": 1
  }' | python3 -m json.tool 2>/dev/null || echo "Failed to parse response as JSON"
echo -e "\n"

# Test 5: Network Performance Test
echo -e "${BLUE}Test 5: Testing Network Latency${NC}"
echo "Making 5 requests to measure response time..."
for i in {1..5}; do
    START=$(date +%s.%N)
    curl -s -X POST "${VALIDATION_SERVER}/validate" \
      -H "Content-Type: application/json" \
      -d '{
        "proxy": "1.1.1.1:80",
        "proxy_type": "http",
        "ping_count": 1
      }' > /dev/null
    END=$(date +%s.%N)
    DIFF=$(echo "$END - $START" | bc)
    echo "Request $i: ${DIFF}s"
done
echo -e "\n"

echo -e "${BLUE}All tests completed!${NC}"
echo -e "If all tests passed, your scraper can communicate with the validation server."
echo -e "If any test failed, check:"
echo -e "1. SSH tunnel is active (ssh -R 9100:localhost:9100)"
echo -e "2. Validation server is running on your local machine"
echo -e "3. Port 9100 is not being used by another process"
echo -e "4. Your SSH connection is stable"

# Print validation server info
echo -e "\n${BLUE}Validation Server Info:${NC}"
curl -s "${VALIDATION_SERVER}/docs" > /dev/null
if [ $? -eq 0 ]; then
    echo -e "API Documentation: ${GREEN}${VALIDATION_SERVER}/docs${NC}"
    echo -e "OpenAPI Schema: ${GREEN}${VALIDATION_SERVER}/openapi.json${NC}"
fi 