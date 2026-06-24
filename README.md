# IP-API MCP Server

현재 공인 IP 또는 특정 IP 주소의 대략적인 위치 정보를 조회하는 Python FastMCP 서버입니다.

`ip-api.com`의 무료 JSON API를 MCP tool로 감싸서, AI 클라이언트가 사용자의 현재 네트워크 위치나 특정 IP의 지역 기반 컨텍스트를 확인할 수 있게 합니다.

## 기능

- `lookup_ip_location`
  - `ip_address`를 생략하면 MCP 서버가 실행 중인 컴퓨터의 공인 IP 위치를 조회합니다.
  - `ip_address`를 넘기면 해당 IPv4 또는 IPv6 주소의 위치를 조회합니다.
  - 국가, 도시, ISP, 위도, 경도, 데이터 출처를 반환합니다.
  - 사용자에게 보여주기 좋은 한국어 `message`도 함께 반환합니다.
- `GET /health`
  - 서버 상태 확인용 엔드포인트입니다.
- `GET /my-ip-location`
  - ChatGPT App UI iframe이나 브라우저에서 호출할 수 있는 엔드포인트입니다.
  - `X-Forwarded-For`, `X-Real-IP`, request client 순서로 브라우저 요청 IP를 읽고 위치를 조회합니다.
- `POST /mcp`
  - FastMCP HTTP transport 엔드포인트입니다.

## 무료 사용 조건

`ip-api.com`은 비상업적 이용에 한해 API 키 없이 무료로 사용할 수 있습니다.

- 무료 조건: 비상업적 이용, 과제 포함
- API 키: 불필요
- 호출 제한: 분당 45회
- 본인 IP 조회: `http://ip-api.com/json`
- 특정 IP 조회: `http://ip-api.com/json/8.8.8.8`

이 서버는 프로세스 내부에서 분당 45회 제한을 방어합니다. 상업적 이용 여부와 최신 정책은 `ip-api.com`의 공식 약관을 확인하세요.

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python server.py
```

기본 MCP 엔드포인트:

```text
http://localhost:8000/mcp
```

상태 확인:

```bash
curl http://localhost:8000/health
```

브라우저 요청 IP 기준 위치 확인:

```bash
curl http://localhost:8000/my-ip-location
```

포트를 바꾸려면 `PORT` 환경 변수를 사용합니다.

```bash
PORT=9000 python server.py
```

## MCP Tool

### `lookup_ip_location`

IP 주소 위치 정보를 조회합니다.

입력:

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `ip_address` | `string` 또는 `null` | 아니오 | 조회할 IPv4 또는 IPv6 주소입니다. 생략하면 현재 MCP 서버가 실행 중인 환경의 공인 IP를 조회합니다. |

본인 공인 IP 조회:

```json
{}
```

특정 IP 조회:

```json
{
  "ip_address": "8.8.8.8"
}
```

출력 예시:

```json
{
  "query": "8.8.8.8",
  "country": "United States",
  "city": "Ashburn",
  "isp": "Google LLC",
  "latitude": 39.03,
  "longitude": -77.5,
  "source": "ip-api.com",
  "message": "IP 8.8.8.8 위치는 United States, Ashburn이며 ISP는 Google LLC입니다."
}
```

## MCP 클라이언트 테스트

서버를 실행한 뒤 다른 터미널에서 실행합니다.

```bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp") as client:
        result = await client.call_tool(
            "lookup_ip_location",
            {"ip_address": "8.8.8.8"},
        )
        print(result.data)

asyncio.run(main())
PY
```

현재 공인 IP를 자동 조회하려면 빈 입력을 넘깁니다.

```python
{}
```

## ChatGPT App 브라우저 IP 조회

ChatGPT에서 MCP tool을 호출하면 요청 주체는 사용자의 브라우저가 아니라 ChatGPT/OpenAI 쪽 MCP 호출 인프라입니다. 그래서 `lookup_ip_location`에 빈 입력을 넘기면 실제 사용자 IP가 아니라 서버나 중간 인프라 기준 IP가 조회될 수 있습니다.

사용자 브라우저의 공인 IP 기준 위치가 필요하면 ChatGPT App UI iframe 또는 일반 브라우저에서 아래 HTTP route를 직접 호출하세요.

```text
https://your-render-service.onrender.com/my-ip-location
```

브라우저 JavaScript 예시:

```js
const response = await fetch("https://your-render-service.onrender.com/my-ip-location");
const location = await response.json();
console.log(location);
```

응답 예시:

```json
{
  "query": "203.0.113.10",
  "country": "South Korea",
  "city": "Seoul",
  "isp": "Example ISP",
  "latitude": 37.5665,
  "longitude": 126.978,
  "source": "ip-api.com"
}
```

이 route는 프록시 환경에서 흔히 전달되는 `X-Forwarded-For` 헤더의 첫 번째 IP를 우선 사용합니다. 이 값은 지역 컨텍스트 표시에는 유용하지만, 인증이나 보안 차단 같은 중요한 판단에는 그대로 신뢰하지 마세요.

## 테스트

```bash
source .venv/bin/activate
pytest -q
```

현재 테스트 범위:

- 본인 공인 IP 조회 엔드포인트 생성
- 특정 IP 조회 엔드포인트 생성
- 응답 필드 정규화
- 잘못된 IP 입력 거부
- `ip-api.com` 실패 응답 처리
- FastMCP tool payload 생성
- 브라우저 요청 IP 추출
- `/my-ip-location` route 응답
- 분당 호출 제한 처리

## 파일 구조

```text
.
├── server.py
├── requirements.txt
├── requirements-dev.txt
└── tests/
    └── test_server.py
```

## 참고

- 위치 정보는 IP 기반의 대략적인 정보이며 GPS처럼 정확하지 않습니다.
- 무료 API는 HTTP 엔드포인트를 사용합니다.
- 서버 재시작 시 인메모리 호출 제한 기록은 초기화됩니다.
- 여러 서버 프로세스를 동시에 실행하면 호출 제한이 프로세스별로 적용됩니다.
