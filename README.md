# 청림유도관 관리 앱

Django 기반 유도관 출석·일정·회원 관리 PWA

- **URL**: https://cheonglimjudo.pythonanywhere.com
- **호스팅**: PythonAnywhere
- **스택**: Django 4.2 · SQLite · Bootstrap 5 · PWA

---

## 배포 이력

### v1.8 — 2026-06-28
- Web Push 알림 추가: 같은 슬롯에 누군가 출석 등록/취소 시 푸시 알림 수신
- 홈 화면 하단 버전 표시 + 업데이트 이력 모달
- 테스트 86개로 확장 (Push 구독·해제·알림 생성 시나리오 추가)
- VAPID 키 환경변수 분리 (WSGI 파일에서 관리)

### v1.7 — 2026-06-26
- 전체 기능 테스트 77개 추가 (모델·인증·출석·프로필·공지·회원·회비·사용자·대시보드·출석확인)
- 출석 토글 NameError 버그 수정 (target_date 파싱 순서 오류)
- `attendance/confirm/toggle/` URL이 날짜 파라미터로 잡히던 라우팅 버그 수정

### v1.6 — 2026-06-24
- 홈 화면 프로필 카드 원형에 띠 색상 적용, 유단자는 로마 숫자(Ⅰ~Ⅵ) 표시
- 홈 하단에 관장 이름 표시 (단수 높은 순 정렬)
- 주황띠 선택지 전체 제거
- 출석 시간대 요일별 분리: 월~금 3타임(18:00·19:30·21:00), 토 2타임(11:00·13:00), 일 3타임(사유회·13:00·15:00)
- 내 정보 수정: 사용자 이름 변경(중복 체크)·띠 변경·비밀번호 변경 기능 추가
- 회원가입 성공 시 토스트 메시지 표시, 이중 제출 방지 버튼 처리
- 내 정보 수정 500 에러 수정 (잘못된 import 제거)

### v1.5 — 2026-06-22
- 앱 아이콘 교체: 청림유도관 로고로 변경

### v1.4 — 2026-06-21
- 회비 납부 관리 기능 추가 (월별 납부 현황·토글)
- 띠 승급 이력 기능 추가 (승급 기록·삭제, 회원 상세 페이지 통합)
- PWA 설정: 홈 화면 설치, iOS standalone 모드, 아이콘 192/512px
- 사용자 관리 페이지 추가 (관장 권한·활성화 토글)
- 대시보드 빠른 메뉴 추가
- 배포 설정: DEBUG/SECRET_KEY 환경변수 분리, requirements.txt 정리

### v1.0 — 2026-06-21
- 최초 배포
- 회원 관리 (CRUD·체급·연락처)
- 출석 예정 등록·취소 (주간/월간 보기)
- 훈련 일정·대회 일정 관리
- 공지사항 (핀 고정)
- 알림 시스템
- 관장/관원 권한 분리

---

## 배포 방법 (PythonAnywhere)

```bash
cd ~/judo-app && git pull && python manage.py migrate && touch /var/www/cheonglimjudo_pythonanywhere_com_wsgi.py
```

마이그레이션 변경이 없으면 `migrate` 생략 가능.

### Web Push 환경변수 (WSGI 파일에 설정)
```python
os.environ['VAPID_PRIVATE_KEY'] = '...'
os.environ['VAPID_PUBLIC_KEY']  = '...'
```

---

## 테스트 실행

```bash
python manage.py test schedule accounts
```

총 86개 테스트, 전 기능 커버.
