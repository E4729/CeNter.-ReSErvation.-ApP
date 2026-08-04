import re
from dataclasses import dataclass, field

import streamlit as st


# ==================================================
# 기본 설정
# ==================================================

st.set_page_config(
    page_title="센터 예약 리스트🧘🏻‍♀️🌿",
    page_icon="🧘🏻‍♀️",
    layout="wide",
)

st.title("센터 예약 리스트🧘🏻‍♀️🌿")

st.write(
    "카카오톡 예약 신청 내용을 붙여넣으면 요일별로 자동 정리합니다."
)


# ==================================================
# 입력창
# ==================================================

input_text = st.text_area(
    "예약 신청 내용",
    height=420,
    placeholder="""예시)

✅유하나
월요일 오후1시~ (서브케어 듀엣 희망)

✅체험단 김순덕
금요일 14~16시

✅체험단 김성은
수요일 10시~2시
목요일 10시~2시
금요일 10시~2시

✅김태림
월, 수, 금요일 19시~21시
(교정, 원장님 상담 희망)

✅권유림
화요일 21시~22시
금요일 19:20
""",
)

run_button = st.button(
    "📝 예약 정리하기",
    use_container_width=True,
)


# ==================================================
# 상수
# ==================================================

DAY_ORDER = [
    "월",
    "화",
    "수",
    "목",
    "금",
    "토",
    "일",
]

FREE_WORDS = [
    "free",
    "다 가능",
    "다가능",
    "아무때나",
    "아무 때나",
    "언제든",
]

IGNORE_WORDS = [
    "감사합니다",
    "감사합니다.",
    "고맙습니다",
    "부탁드립니다",
    "부탁 드립니다",
    "부탁드려요",
    "부탁 드려요",
    "가능할까요",
    "가능할까요?",
    "입니다",
]

MEMO_RULES = {

    "서브 희망": [
        "서브",
        "서브케어",
        "서브 케어",
    ],

    "교정 희망": [
        "교정",
        "교정케어",
        "교정 케어",
    ],

    "포톤 X": [
        "포톤 제외",
        "포톤제외",
        "포톤 빼주세요",
        "포톤말고",
    ],

    "D 상담": [
        "원장님 상담",
        "상담",
    ],

    "듀엣 희망": [
        "듀엣",
    ],

    "1:1 희망": [
        "1:1",
    ],

    "결제": [
        "결제",
    ],

    "격일 희망": [
        "격일",
        "이틀 연속",
    ],
}


# ==================================================
# 정규식
# ==================================================

MEMBER_PATTERN = re.compile(
    r"^\s*✅\s*(.+)$"
)

DAY_PATTERN = re.compile(
    r"(월|화|수|목|금|토|일)(?:요일)?"
)

TIME_PATTERN = re.compile(
    r"(?:(오전|오후)\s*)?"
    r"(\d{1,2})"
    r"(?::(\d{2}))?"
)


# ==================================================
# 데이터 구조
# ==================================================

@dataclass
class Reservation:

    day: str

    start_hour: int

    start_minute: int

    end_hour: int | None = None

    end_minute: int | None = None

    is_free: bool = False

    is_after: bool = False

    raw: str = ""

    order: int = 0

    def display(self) -> str:

        if self.is_free:
            return "Free"

        def fmt(hour, minute, end=False):

            if minute == 0:

                if end:
                    return f"{hour}시"

                return str(hour)

            return f"{hour}:{minute:02}"

        start = fmt(
            self.start_hour,
            self.start_minute,
        )
        
        if self.end_hour is not None:
        
            end = fmt(
                self.end_hour,
                self.end_minute,
                end=True,
            )

            return f"{start}~{end}"

        if self.is_after:

            if self.start_minute == 0:
                return f"{self.start_hour}시~"

            return f"{self.start_hour}:{self.start_minute:02}~"

@dataclass
class Member:

    name: str

    reservations: list[Reservation] = field(default_factory=list)

    memos: list[str] = field(default_factory=list)

    total_count: int = 0


@dataclass
class ReviewItem:

    name: str

    reason: str

    raw: str
    
@dataclass
class ReviewItem:

    name: str

    reason: str

    raw: str


# ==================================================
# 전역 저장소
# ==================================================

review_items: list[ReviewItem] = []

# ==================================================
# 공통 함수
# ==================================================

def clean_text(text: str) -> str:

    return re.sub(r"\s+", " ", text).strip()


def remove_ignore_words(text: str) -> str:

    for word in IGNORE_WORDS:
        text = text.replace(word, "")

    return clean_text(text)


def normalize_day(text: str) -> str:

    return text.replace("요일", "")


def is_free(text: str) -> bool:

    lower = text.lower()

    return any(
        word.lower() in lower
        for word in FREE_WORDS
    )


def normalize_memos(text: str) -> list[str]:

    result = []

    for memo, keywords in MEMO_RULES.items():

        for keyword in keywords:

            if keyword in text:

                if memo not in result:
                    result.append(memo)

    return result


# ==================================================
# 시간 변환
# ==================================================

def convert_hour(hour: int, ampm: str | None) -> int:

    if ampm == "오후":

        if hour != 12:
            return hour + 12

        return hour

    if ampm == "오전":

        if hour == 12:
            return 0

        return hour

    # 오전/오후 표시 없을 경우
    # 1~8시는 오후로 간주

    if 1 <= hour <= 8:
        return hour + 12

    return hour


def format_time(hour: int, minute: int = 0) -> str:

    return f"{hour:02}:{minute:02}"


def extract_first_time(text: str):

    if is_free(text):
        return "Free"

    match = TIME_PATTERN.search(text)

    if not match:
        return None

    ampm = match.group(1)

    hour = int(match.group(2))

    minute = int(match.group(3) or 0)

    hour = convert_hour(hour, ampm)

    return format_time(hour, minute)


# ==================================================
# 정렬
# ==================================================

def sort_key(time_text: str):

    if time_text == "Free":
        return (-1, -1)

    if not time_text:
        return (999, 999)

    # 시간 범위면 시작 시간만 사용
    if "~" in time_text:
        time_text = time_text.split("~")[0]

    try:
        hour_str, minute_str = time_text.split(":", 1)
        return (int(hour_str), int(minute_str))
    except:
        return (999, 999)
    
# ==================================================
# 회원 분리
# ==================================================

def split_member_blocks(text: str) -> list[str]:

    text = text.replace("\r", "")

    lines = text.split("\n")

    blocks = []

    current = []

    for line in lines:

        if MEMBER_PATTERN.match(line):

            if current:
                blocks.append("\n".join(current))

            current = [line]

        else:

            if current:
                current.append(line)

    if current:
        blocks.append("\n".join(current))

    return blocks


def get_member_name(first_line: str) -> str:

    match = MEMBER_PATTERN.match(first_line)

    if not match:
        return ""

    return clean_text(match.group(1))


# ==================================================
# 예약줄 / 메모줄 구분
# ==================================================

def extract_days(text: str) -> list[str]:

    text = normalize_day(text)

    text = (
        text.replace("&", ",")
            .replace("/", ",")
            .replace("·", ",")
    )

    days = DAY_PATTERN.findall(text)

    result = []

    for day in days:

        if day not in result:
            result.append(day)

    return result


def is_schedule_line(text: str) -> bool:

    if extract_days(text):
        return True

    if is_free(text):
        return True

    if TIME_PATTERN.search(text):
        return True

    return False


# ==================================================
# 회원 파싱
# ==================================================

def parse_member_block(block: str) -> Member | None:

    lines = [
        remove_ignore_words(line)
        for line in block.split("\n")
        if clean_text(line)
    ]

    if not lines:
        return None

    member = Member(
        name=get_member_name(lines[0])
    )

    for line in lines[1:]:

        if not line:
            continue

        if is_schedule_line(line):

            member.reservations.append(
                Reservation(
                    day="",
                    start_hour=0,
                    start_minute=0,
                    raw=line,
                )
            )

        else:

            for memo in normalize_memos(line):

                if memo not in member.memos:
                    member.memos.append(memo)

    member.memos = list(dict.fromkeys(member.memos))

    return member

def parse_members(text: str) -> list[Member]:

    result = []

    blocks = split_member_blocks(text)

    for block in blocks:

        member = parse_member_block(block)

        if member:
            result.append(member)

    return result

# ==================================================
# 시간 파싱
# ==================================================

TIME_RANGE_PATTERN = re.compile(
    r"(?:(오전|오후)\s*)?"
    r"(\d{1,2})"
    r"(?::(\d{2}))?"
    r"\s*(?:시)?"
    r"\s*(?:~|-|–)?\s*"
    r"(?:(오전|오후)\s*)?"
    r"(\d{1,2})?"
    r"(?::(\d{2}))?"
)


def parse_time(text: str):

    if is_free(text):

        return {
            "is_free": True,
        }

    match = TIME_RANGE_PATTERN.search(text)

    if not match:
        return None

    start_ampm = match.group(1)
    start_hour = convert_hour(
        int(match.group(2)),
        start_ampm,
    )

    start_minute = int(match.group(3) or 0)

    if not match.group(5):

        return {
            "start_hour": start_hour,
            "start_minute": start_minute,
            "is_after": "~" in text or "이후" in text,
        }

    end_ampm = match.group(4)

    end_hour = convert_hour(
        int(match.group(5)),
        end_ampm,
    )

    end_minute = int(match.group(6) or 0)

    return {
        "start_hour": start_hour,
        "start_minute": start_minute,
        "end_hour": end_hour,
        "end_minute": end_minute,
        "is_after": False,
    }

# ==================================================
# 예약 생성
# ==================================================

def build_member_reservations(member: Member):

    new_reservations = []

    for reservation in member.reservations:

        raw = reservation.raw

        days = extract_days(raw)

        time_info = parse_time(raw)

        if not days:

            review_items.append(
                ReviewItem(
                    member.name,
                    "요일 인식 실패",
                    raw,
                )
            )

            continue

        if not time_info:

            review_items.append(
                ReviewItem(
                    member.name,
                    "시간 인식 실패",
                    raw,
                )
            )

            continue

        for day in days:

            new_reservations.append(

                Reservation(

                    day=day,

                    start_hour=time_info.get(
                        "start_hour",
                        0,
                    ),

                    start_minute=time_info.get(
                        "start_minute",
                        0,
                    ),

                    end_hour=time_info.get(
                        "end_hour",
                    ),

                    end_minute=time_info.get(
                        "end_minute",
                    ),

                    is_free=time_info.get(
                        "is_free",
                        False,
                    ),

                    is_after=time_info.get(
                        "is_after",
                        False,
                    ),

                    raw=raw,
                )

            )

    member.reservations = new_reservations

def build_all_reservations(members):

    for member in members:

        build_member_reservations(member)

# ==================================================
# 출력용 정렬
# ==================================================

def reservation_sort_key(reservation: Reservation):

    if reservation.is_free:
        return (-1, -1)

    return (
        reservation.start_hour,
        reservation.start_minute,
    )

from collections import defaultdict

def build_day_table(members: list[Member]):

    day_table = defaultdict(list)

    for member in members:

        member.total_count = len(member.reservations)

        # 월~일 순서 기준 번호 저장
        reservation_numbers = {}
    
        ordered = sorted(
            member.reservations,
            key=lambda r: (
                DAY_ORDER.index(r.day),
                reservation_sort_key(r),
            ),
        )
    
        for index, reservation in enumerate(ordered, start=1):
            reservation_numbers[id(reservation)] = index

        # 출력용으로만 정렬
        sorted_reservations = sorted(
            member.reservations,
            key=reservation_sort_key,
        )

        memo = ""

        if member.memos:
            memo = " (" + ", ".join(member.memos) + ")"

        for reservation in sorted_reservations:

            number = reservation_numbers[id(reservation)]

            day_table[reservation.day].append(
                {
                    "sort": reservation_sort_key(reservation),
                    "text": (
                        f"{member.name} "
                        f"{reservation.display()} "
                        f"({member.total_count}-{number})"
                        f"{memo}"
                    ),
                }
            )

    return day_table

def sort_day_table(day_table):

    for day in DAY_ORDER:

        day_table[day].sort(
            key=lambda x: x["sort"]
        )

    return day_table

def build_copy_text(day_table):

    result = []

    for day in DAY_ORDER:

        result.append(
            f"{DAY_NAME[day]} ({len(day_table[day])}명)"
        )

        if len(day_table[day]) == 0:

            result.append("예약 X")

        else:

            for item in day_table[day]:
                result.append("• " + item["text"])

        result.append("")

    return "\n".join(result)

# ==================================================
# 실행
# ==================================================

DAY_NAME = {
    "월": "월요일",
    "화": "화요일",
    "수": "수요일",
    "목": "목요일",
    "금": "금요일",
    "토": "토요일",
    "일": "일요일",
}


if run_button:

    review_items.clear()

    members = parse_members(input_text)

    build_all_reservations(members)

    day_table = build_day_table(members)

    day_table = sort_day_table(day_table)

    copy_text = build_copy_text(day_table)

    total_members = len(members)

    total_reservations = sum(
        len(member.reservations)
        for member in members
    )

    st.success(
        f"👥 회원 {total_members}명   |   📅 예약 신청 {total_reservations}건"
    )

if review_items:

    st.divider()

    st.error(
        f"⚠️ 검토 필요 {len(review_items)}건"
    )

    for item in review_items:

        st.warning(
            f"{item.name}\n\n"
            f"사유 : {item.reason}\n\n"
            f"원문 : {item.raw}"
        )

st.divider()

st.code(copy_text)