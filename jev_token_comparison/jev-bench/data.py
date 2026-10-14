"""Benchmark inputs: 20 Korean support tickets and the 3 shared questions."""

# kind: short / angry / urgent (a mix, for the CSV only; not used in scoring)
TICKETS = [
    {"id": 1, "kind": "short", "text": "결제 영수증 어디서 다운받나요?"},
    {"id": 2, "kind": "short", "text": "비밀번호 변경 메뉴가 안 보여요."},
    {"id": 3, "kind": "short", "text": "팀 요금제 견적 받을 수 있을까요? 인원은 30명입니다."},
    {"id": 4, "kind": "short", "text": "앱이 업데이트 후 자꾸 꺼져요."},
    {"id": 5, "kind": "short", "text": "연간 결제로 바꾸면 할인되나요?"},
    {"id": 6, "kind": "short", "text": "API 문서 링크가 404 나옵니다."},
    {"id": 7, "kind": "short", "text": "엔터프라이즈 플랜 데모 신청하고 싶습니다."},
    {
        "id": 8,
        "kind": "angry",
        "text": "이번 달에 결제가 두 번 됐습니다. 벌써 세 번째 문의인데 아무도 답을 안 주네요. "
        "도대체 고객을 뭘로 보는 겁니까? 당장 환불하세요.",
    },
    {
        "id": 9,
        "kind": "angry",
        "text": "해지했는데 또 돈이 빠져나갔어요. 이거 사기 아닌가요? 소비자원에 신고하겠습니다.",
    },
    {
        "id": 10,
        "kind": "angry",
        "text": "업데이트할 때마다 기능이 망가지네요. 테스트는 하고 배포하는 건가요? 진짜 최악입니다.",
    },
    {
        "id": 11,
        "kind": "angry",
        "text": "영업 담당자가 약속한 할인가가 계약서에 반영이 안 됐습니다. "
        "말 바꾸는 회사랑은 거래 못 하겠네요.",
    },
    {
        "id": 12,
        "kind": "angry",
        "text": "안녕하세요. 지난주에 문의드린 로그인 오류가 아직 해결되지 않았습니다. "
        "업무에 지장이 있어서 조금 답답하네요. 확인 부탁드립니다.",
    },
    {
        "id": 13,
        "kind": "angry",
        "text": "청구서 금액이 안내받은 것과 다릅니다. 불편하지만 일단 내역 확인 부탁드려요.",
    },
    {
        "id": 14,
        "kind": "urgent",
        "text": "지금 운영 서버 전체가 다운됐습니다! 결제 API가 500 에러만 반환해요. "
        "고객 주문이 전부 실패하고 있습니다. 바로 연락 주세요!!",
    },
    {
        "id": 15,
        "kind": "urgent",
        "text": "오늘 자정에 카드 만료로 구독이 끊긴다는 메일을 받았습니다. "
        "내일 오전 고객 시연이 있어서 오늘 안에 결제수단을 꼭 바꿔야 해요.",
    },
    {
        "id": 16,
        "kind": "urgent",
        "text": "1시간 뒤 이사회 보고 전에 엔터프라이즈 계약 견적서가 필요합니다. 최대한 빨리 보내주세요.",
    },
    {
        "id": 17,
        "kind": "urgent",
        "text": "보안 경고: 우리 계정에서 모르는 IP로 API 키가 계속 사용되고 있습니다. "
        "키 유출이 의심됩니다. 즉시 차단 방법 알려주세요.",
    },
    {
        "id": 18,
        "kind": "urgent",
        "text": "몇 시간째 대시보드에 로그인이 안 되고 있어요. 오늘 마감 보고서를 뽑아야 하는데 "
        "정말 미치겠습니다. 이게 몇 번째인지 모르겠네요. 빨리 고쳐주세요.",
    },
    {
        "id": 19,
        "kind": "short",
        "text": "안녕하세요. 다음 분기에 사용자 수를 늘릴 계획인데, 추가 좌석 가격표를 받아볼 수 있을까요? "
        "급한 건 아니고 다음 달 예산 회의 때 참고하려고 합니다. 감사합니다.",
    },
    {
        "id": 20,
        "kind": "angry",
        "text": "웹훅 재시도 로직 관련 문의입니다. 지난 3일 동안 이벤트가 중복으로 들어와 데이터가 "
        "꼬였고, 정리하느라 팀 전체가 야근했습니다. 문서에는 멱등성 키를 보장한다고 되어 있는데 "
        "실제로는 아니네요. 원인 분석 보고서와 재발 방지 대책을 요청합니다.",
    },
]

# Jev request format; providers.py converts the same dict into a Claude tool schema.
QUESTIONS = {
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this customer ticket?",
        "criteria": {
            "billing": "Payments, invoices, refunds, subscriptions, payment methods",
            "technical": "Bugs, outages, login problems, API or integration issues, security incidents",
            "sales": "Quotes, pricing for new or expanded plans, demos, contract negotiations",
        },
    },
    "frustration": {
        "type": "score",
        "instructions": "How frustrated is the customer?",
        "criteria": [
            "Calm: neutral, no sign of frustration",
            "Frustrated but polite: dissatisfaction expressed courteously",
            "Very angry: hostile, accusatory, or threatening tone",
        ],
    },
    "is_urgent": {
        "type": "noul",
        "instructions": "Is this ticket urgent or time-sensitive, needing a response within hours?",
    },
}
