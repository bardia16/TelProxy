#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

VALIDATION_SERVER="http://100.76.79.59:8000"

echo -e "${BLUE}Testing Connection to Validation Server${NC}\n"

# Test 1: Basic connectivity test
echo -e "${BLUE}Test 1: Testing Basic Connectivity${NC}"
if curl -s --connect-timeout 5 "${VALIDATION_SERVER}/validate" -o /dev/null; then
    echo -e "${GREEN}✓ Can reach validation server${NC}"
else
    echo -e "${RED}✗ Cannot reach validation server${NC}"
fi
echo -e "\n"

# Test 2: API Response Test
echo -e "${BLUE}Test 2: Testing API Response${NC}"
RESPONSE=$(curl -s -X POST "${VALIDATION_SERVER}/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "proxy": "1.1.1.1:80",
    "proxy_type": "http",
    "ping_count": 1
  }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API is responding${NC}"
    echo "Response:"
    echo "$RESPONSE" | python3 -m json.tool
else
    echo -e "${RED}✗ API request failed${NC}"
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
  }" | python3 -m json.tool
echo -e "\n"

# Test 4: MTProto Test (Telegram Connectivity)
echo -e "${BLUE}Test 4: Testing MTProto Validation${NC}"
curl -s -X POST "${VALIDATION_SERVER}/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "proxy": "1.1.1.1:443",
    "proxy_type": "mtproto",
    "ping_count": 1
  }' | python3 -m json.tool
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
echo -e "1. Tailscale connection status"
echo -e "2. Validation server is running"
echo -e "3. Port 8000 is open on the validation server"
echo -e "4. No firewall rules blocking the connection" 