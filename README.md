# IP-API MCP Server

IP 주소를 기준으로 대략적인 위치 정보를 조회하는 Python FastMCP 서버입니다.

이 서버는 [`ip-api.com`](http://ip-api.com/)의 무료 JSON API를 MCP tool로 감싸서, AI 클라이언트가 사용자의 현재 네트워크 위치나 특정 IP의 지역 기반 컨텍스트를 확인할 수 있게 합니다.

## 주요 기능

- 요청을 보낸 기기의 IP 기준 위치 조회
- 특정 IPv4 또는 IPv6 주소 기준 위치 조회
- 국가, 도시, ISP, 위도, 경도 정보 반환
- API 키 없이 사용 가능
- `ip-api.com` 무료 호출 제한인 분당 45회를 서버 프로세스 안에서 방어
- Python `FastMCP` 기반 stdio MCP 서버

## 무료 사용 조건

`ip-api.com`은 비상업적 이용에 한해 API 키 없이 무료로 사용할 수 있습니다.

- 무료 조건: 비상업적 이용, 과제 포함
- API 키: 불필요
- 호출 제한: 분당 45회
- 공식 엔드포인트:
  - 본인 IP 조회: `http://ip-api.com/json`
  - 특정 IP 조회: `http://ip-api.com/json/8.8.8.8`

상업적 이용 여부와 최신 정책은 `ip-api.com`의 공식 약관을 확인하세요.

## 요구 사항

- Python 3.11 이상
- `uv`

의존성은 `pyproject.toml`에 정의되어 있습니다.

주요 패키지:

- `mcp[cli]`
- `httpx`
- `pytest`
- `pytest-asyncio`

## 설치

프로젝트 루트에서 다음 명령을 실행합니다.

```bash
uv sync
```

## 실행

stdio MCP 서버로 실행합니다.

```bash
uv run ip-api-mcp
```

동일한 실행 진입점은 다음 파일에 정의되어 있습니다.

```text
src/ip_api_mcp/server.py
```

## MCP Tool

### `lookup_ip_location`

IP 주소 위치 정보를 조회합니다.

#### 입력

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `ip_address` | `string` 또는 `null` | 아니오 | 조회할 IPv4 또는 IPv6 주소입니다. 생략하면 요청을 보낸 기기의 IP를 기준으로 조회합니다. |

#### 입력 예시: 본인 IP 조회

```json
{}
```

#### 입력 예시: 특정 IP 조회

```json
{
  "ip_address": "8.8.8.8"
}
```

#### 출력

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `query` | `string` | 조회된 IP 주소 |
| `country` | `string` | 국가 |
| `city` | `string` | 도시 |
| `isp` | `string` | 인터넷 서비스 제공자 |
| `latitude` | `number` | 위도 |
| `longitude` | `number` | 경도 |
| `source` | `string` | 데이터 출처. 현재 값은 `ip-api.com` |

#### 출력 예시

```json
{
  "query": "8.8.8.8",
  "country": "United States",
  "city": "Ashburn",
  "isp": "Google LLC",
  "latitude": 39.03,
  "longitude": -77.5,
  "source": "ip-api.com"
}
```

## MCP 클라이언트 설정 예시

MCP 클라이언트가 stdio 서버를 실행할 수 있다면 아래처럼 연결할 수 있습니다.

```json
{
  "mcpServers": {
    "ip-api": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/sanghyoukjin/DonguramiProjects/IP-API",
        "run",
        "ip-api-mcp"
      ]
    }
  }
}
```

## 사용 예시

AI 클라이언트에서 다음과 같은 요청을 처리할 때 사용할 수 있습니다.

```text
현재 내 위치 보안 상태나 지역 기반 컨텍스트를 분석해 줘.
```

```text
8.8.8.8 IP의 국가, 도시, ISP를 조회해 줘.
```

## 에러 처리

서버는 다음 상황을 명확한 에러로 반환합니다.

- 유효하지 않은 IP 주소 입력
- `ip-api.com`이 실패 상태를 반환하는 경우
- HTTP 요청 실패
- 1분 안에 45회를 초과하는 호출

IP 주소 검증은 Python 표준 라이브러리 `ipaddress`를 사용합니다.

## 테스트

전체 테스트를 실행합니다.

```bash
uv run pytest -q
```

현재 테스트 범위:

- 본인 IP 조회 엔드포인트 생성
- 특정 IP 조회 엔드포인트 생성
- 응답 필드 정규화
- 잘못된 IP 입력 거부
- `ip-api.com` 실패 응답 처리
- 분당 호출 제한 처리
- FastMCP tool 등록 및 호출

## 프로젝트 구조

```text
.
├── README.md
├── pyproject.toml
├── src
│   └── ip_api_mcp
│       ├── __init__.py
│       ├── client.py
│       ├── rate_limit.py
│       └── server.py
└── tests
    ├── test_client.py
    └── test_server.py
```

## 구현 메모

- `server.py`: FastMCP 서버와 `lookup_ip_location` tool 정의
- `client.py`: `ip-api.com` HTTP 호출, IP 검증, 응답 정규화
- `rate_limit.py`: 프로세스 내부 메모리 기반 호출 제한
- `tests/`: 외부 API 호출 없이 동작하는 단위 테스트

## 주의 사항

- 위치 정보는 IP 기반의 대략적인 정보이며 GPS처럼 정확하지 않습니다.
- 무료 API는 HTTP 엔드포인트를 사용합니다.
- 서버 재시작 시 인메모리 호출 제한 기록은 초기화됩니다.
- 여러 서버 프로세스를 동시에 실행하면 호출 제한이 프로세스별로 적용됩니다.
