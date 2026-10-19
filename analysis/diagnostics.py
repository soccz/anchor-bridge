"""공개 합성 예제로 실행하는 검증 도구. 실제 지역 결과는 포함하지 않는다."""

from datetime import date
from math import isfinite, sqrt


def correlation(x, y):
    """같은 월의 두 계열을 비교한다. 상수 계열은 관계를 정의할 수 없다."""
    if len(x) != len(y) or len(x) < 3:
        raise ValueError("같은 길이의 관측 3개 이상이 필요합니다")
    if not all(isfinite(v) for v in [*x, *y]):
        raise ValueError("관측값이 유한해야 합니다")
    dx = [v - sum(x) / len(x) for v in x]
    dy = [v - sum(y) / len(y) for v in y]
    denominator = sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    return sum(a * b for a, b in zip(dx, dy)) / denominator if denominator else None


def leave_one_out(x, y):
    """한 달을 빼며 관계가 특정 관측에 의존하는지 확인한다."""
    if len(x) != len(y) or len(x) < 4:
        raise ValueError("같은 길이의 관측 4개 이상이 필요합니다")
    return [correlation(x[:i] + x[i + 1:], y[:i] + y[i + 1:]) for i in range(len(x))]


def eligibility_change(all_value, known_value, segment_value, threshold=1):
    """전체→연령 확인 집단→특정 연령의 변화에서 관측대상 변경을 분리한다."""
    if not all(isfinite(v) and v >= 0 for v in (all_value, known_value, segment_value)):
        raise ValueError("유한한 비음수 지표가 필요합니다")
    if all_value >= threshold or segment_value < threshold:
        return "새로 자격을 얻은 후보 아님"
    if known_value >= threshold:
        return "관측대상 변경으로 이미 기준 통과"
    return "동일 관측대상에서도 연령 조건에서 기준 통과"


def require_available_before(prediction_date, availability):
    """특징뿐 아니라 적합에 사용한 정답의 관측 종료일도 검사한다.

    이 검사만으로 모든 누수를 탐지할 수는 없다. 호출자가 특징·정답의
    실제 이용 가능일을 빠짐없이 제공해야 한다.
    """
    cutoff = date.fromisoformat(prediction_date)
    future = [name for name, available in availability.items()
              if date.fromisoformat(available) > cutoff]
    if future:
        raise ValueError("예측 시점 이후 정보: " + ", ".join(future))
    return True
