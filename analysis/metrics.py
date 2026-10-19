"""공개용 계산 예제. 제출 분석의 LQ/CLQ 정의를 작은 함수로 옮겼다.

이 모듈은 비공개 전체 파이프라인의 대체물이 아니다. 원자료, 회귀 기준값,
실제 지역별 판정을 포함하지 않는다. 모든 예제 입력은 직접 만든 합성 값이다.
"""

import math


def location_quotient(local_value, local_total, reference_value, reference_total):
    """지역 업종 비중 / 비교 모집단 업종 비중. 정의 불가이면 None."""
    values = (local_value, local_total, reference_value, reference_total)
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("유한한 비음수 값이 필요합니다")
    if local_value > local_total or reference_value > reference_total:
        raise ValueError("업종 값이 합계보다 큽니다")
    if not local_total or not reference_value or not reference_total:
        return None
    return (local_value / local_total) / (reference_value / reference_total)


def conditional_lq(local_value, local_total, local_anchor,
                   reference_value, reference_total, reference_anchor):
    """지역·비교 모집단에서 앵커를 모두 제외한 파트너 특화도."""
    if not 0 <= local_anchor <= local_total or not 0 <= reference_anchor <= reference_total:
        raise ValueError("앵커 값이 합계 범위를 벗어났습니다")
    return location_quotient(local_value, local_total - local_anchor,
                             reference_value, reference_total - reference_anchor)


def standardized_share(shares, weights):
    """같은 연령구성으로 재가중한 비중. 결측층은 임의로 제거하지 않는다."""
    if not shares or len(shares) != len(weights):
        raise ValueError("모든 연령층의 비중·가중치가 필요합니다")
    if any(not math.isfinite(s) or not 0 <= s <= 1 for s in shares):
        raise ValueError("비중은 0~1이어야 합니다")
    if any(not math.isfinite(w) or w < 0 for w in weights) or not math.isclose(sum(weights), 1):
        raise ValueError("가중치는 비음수이고 합이 1이어야 합니다")
    return sum(s * w for s, w in zip(shares, weights))


def evaluate(record):
    """합성 시연의 축약 판정. 추정·검정은 수행하지 않으며 입력 상태를 읽는다.

    금액·건수 자격, 관측, 역행, 점포·거리의 분리를 보여 준다.
    reverse=True는 가정한 입력이며 실제 통계적 유의성 결과가 아니다.
    """
    if record["months"] < 3:
        return "제외", "관측 부족", "관측 기간이 짧아 연결 후보로 판단하기 어렵습니다."
    if min(record["amount_clq"], record["count_clq"]) < 1:
        if (record.get("age_clq") or 0) >= 1 and (record.get("age_count_clq") or 0) >= 1:
            return "추가 확인", "연령 실험", "연령별 자격은 충족하지만 기본 후보와 분리해 공급·거리부터 확인합니다."
        return "제외", "소비기반 부족", "금액과 건수 중 하나 이상이 기준 1에 미달합니다."
    if record["reverse"]:
        return "제외", "역행 가정", "합성 예시에서 강한 역행을 가정해 제외했습니다. 실제 효과를 뜻하지 않습니다."
    if record["stores"] is None or record["coverage"] is None:
        return "추가 확인", "공급 확인", "업종별 점포 집합이 확정되지 않아 공간 조건을 판정하지 않았습니다."
    if not record["stores"]:
        return "제외", "점포 없음", "연결할 점포가 없어 현 단계에서는 실행할 수 없습니다."
    if record["coverage"] < 0.5:
        return "제외", "거리 조건 미달", "직선거리 500m 조건을 만족하는 앵커 점포가 절반 미만입니다."
    return "검토 후보", "조건 충족", "합성 예시의 조건을 충족했습니다. 참여 의사·보행 경로·효과는 별도 확인이 필요합니다."
