---
description: 노트북LM MCP 설치 및 유지보수 워크플로우
---

이 워크플로우는 NotebookLM-MCP 서버가 항상 최신 상태를 유지하고, 인증 상태가 유효하도록 가이드합니다.

### 1단계: 서버 상태 및 버전 확인
현재 설치된 NotebookLM-MCP 버전을 확인하고 업데이트가 필요한지 체크합니다.

// turbo
1. `mcp_notebooklm-mcp_server_info` 툴을 호출하여 버전 정보를 가져옵니다.

### 2단계: 최신 버전으로 업데이트
최신 기능을 사용하기 위해 `notebooklm-mcp-cli` 패키지를 업데이트합니다.

// turbo
2. 다음 명령을 실행합니다:
```powershell
pip install --upgrade notebooklm-mcp-cli
```

### 3단계: 인증 갱신 (nlm login)
NotebookLM 서비스에 접근하기 위해 브라우저 기반 로그인을 수행합니다.

3. 터미널에서 다음 명령을 실행하여 로그인을 완료하세요:
```powershell
nlm login
```

### 4단계: 인증 토큰 동기화
로그인 후 Assistant가 새로운 토큰을 인식할 수 있도록 새로고침을 수행합니다.

// turbo
4. `mcp_notebooklm-mcp_refresh_auth` 툴을 호출합니다.

### 5단계: 최종 상태 검증
노트북 리스트가 정상적으로 조회되는지 확인하여 설치 및 설정을 마무리합니다.

// turbo
5. `mcp_notebooklm-mcp_notebook_list` 툴을 호출하여 상태를 최종 확인합니다.
