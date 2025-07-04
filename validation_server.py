from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import asyncio
import socket
import time
from typing import Optional, List, Union

app = FastAPI(title="Proxy Validation Service")

# Telegram test domains (same as original code)
TELEGRAM_TEST_DOMAINS = ["149.154.175.53", "149.154.167.51"]

class ProxyRequest(BaseModel):
    proxy: str
    proxy_type: Optional[str] = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    ping_count: Optional[int] = 5  # Number of ping measurements
    ping_delay: Optional[float] = 0.2  # Delay between pings

class ValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    ip: Optional[str] = None
    ping: Optional[float] = None  # Average ping in seconds
    ping_measurements: Optional[List[Optional[float]]] = None  # Individual ping measurements can be None
    telegram_connectivity: Optional[bool] = None  # Whether Telegram domains are accessible
    telegram_results: Optional[dict] = None  # Detailed Telegram connectivity results

    class Config:
        json_encoders = {
            float: lambda v: None if v == float('inf') or v == float('-inf') else v
        }

class HealthResponse(BaseModel):
    status: str
    telegram_domains_accessible: bool

def convert_infinite_to_null(value):
    """Convert infinite float values to None for JSON serialization"""
    if isinstance(value, float) and (value == float('inf') or value == float('-inf')):
        return None
    return value

@app.get("/health", response_model=HealthResponse)
async def health_check():
    # Test Telegram domain connectivity
    telegram_test = await test_telegram_connectivity()
    return HealthResponse(
        status="healthy",
        telegram_domains_accessible=telegram_test["success"]
    )

@app.get("/")
async def root():
    return {"status": "running", "endpoints": ["/validate", "/health"]}

async def measure_connection_ping(host: str, port: int, timeout: float = 5) -> Optional[float]:
    try:
        start_time = time.time()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return time.time() - start_time
    except Exception:
        return None  # Return None instead of float('inf')

async def measure_proxy_ping(proxy_req: ProxyRequest) -> List[Optional[float]]:
    try:
        host, port = proxy_req.proxy.split(':')
        port = int(port)
        ping_times = []
        
        for _ in range(proxy_req.ping_count):
            ping_time = await measure_connection_ping(host, port)
            ping_times.append(ping_time)  # Already None if connection failed
            if _ < proxy_req.ping_count - 1:  # Don't sleep after last measurement
                await asyncio.sleep(proxy_req.ping_delay)
        
        return ping_times
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid proxy format. Expected 'host:port', got '{proxy_req.proxy}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error measuring ping: {str(e)}")

async def test_telegram_connectivity() -> dict:
    results = {}
    any_success = False
    
    for domain in TELEGRAM_TEST_DOMAINS:
        try:
            ping_result = await measure_connection_ping(domain, 443)
            success = ping_result is not None
            results[domain] = success
            if success:
                any_success = True
        except Exception as e:
            results[domain] = False
    
    return {
        "success": any_success,
        "domain_results": results
    }

@app.post("/validate", response_model=ValidationResponse)
async def validate_proxy(proxy_req: ProxyRequest):
    try:
        # Measure ping first
        ping_times = await measure_proxy_ping(proxy_req)
        valid_pings = [p for p in ping_times if p is not None]
        avg_ping = sum(valid_pings) / len(valid_pings) if valid_pings else None

        # Initialize telegram test results
        telegram_test_results = None
        telegram_connectivity = None

        # For MTProto proxies, test Telegram connectivity
        if proxy_req.proxy_type == "mtproto":
            telegram_test_results = await test_telegram_connectivity()
            telegram_connectivity = telegram_test_results["success"]

        # Configure the proxy URL based on type
        if proxy_req.proxy_type == "socks5":
            proxy_url = f"socks5://{proxy_req.proxy}"
        else:
            proxy_url = f"http://{proxy_req.proxy}"

        # Add authentication if provided
        if proxy_req.username and proxy_req.password:
            proxy_url = f"{proxy_url.split('://')[0]}://{proxy_req.username}:{proxy_req.password}@{proxy_url.split('://')[1]}"

        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        # For non-MTProto proxies, test with httpbin
        # For MTProto, we only care about Telegram connectivity
        if proxy_req.proxy_type == "mtproto":
            is_valid = telegram_connectivity if telegram_connectivity is not None else True
            return ValidationResponse(
                valid=is_valid,
                ping=avg_ping,
                ping_measurements=ping_times,
                telegram_connectivity=telegram_connectivity,
                telegram_results=telegram_test_results
            )
        else:
            try:
                # Test the proxy with httpbin.org/ip to get the proxied IP
                response = requests.get(
                    "http://httpbin.org/ip",
                    proxies=proxies,
                    timeout=5
                )

                if response.status_code == 200:
                    json_response = response.json()
                    return ValidationResponse(
                        valid=True,
                        ip=json_response.get('origin'),
                        ping=avg_ping,
                        ping_measurements=ping_times
                    )
                else:
                    return ValidationResponse(
                        valid=False,
                        error=f"HTTP {response.status_code}",
                        ping=None,
                        ping_measurements=[None] * proxy_req.ping_count
                    )
            except requests.RequestException as e:
                return ValidationResponse(
                    valid=False,
                    error=f"Proxy test failed: {str(e)}",
                    ping=None,
                    ping_measurements=[None] * proxy_req.ping_count
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9100) 