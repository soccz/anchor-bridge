"""가상 지명과 수치를 직접 작성한 UI 시연용 입력. 실제 자료의 변형본이 아니다."""

from analysis.metrics import evaluate, location_quotient, conditional_lq


def records():
    # id, 가상 지역, 트랙, 앵커, 파트너, LQ, 금액CLQ, 건수CLQ, 관측월,
    # 역행 가정, 점포 수, 거리충족 비율, 연령 금액CLQ, 연령 건수CLQ
    rows = [
        ("gaon-meal", "가온시", "기본", "제과점", "일반한식", .88, 1.32, 1.18, 6, False, 24, .70, None, None),
        ("gaon-snack", "가온시", "기본", "제과점", "스넥", 1.25, 1.875, 1.40, 6, True, 18, .65, None, None),
        ("gaon-course", "가온시", "기본", "제과점", "한정식", .90, 1.35, 1.12, 6, False, None, None, None, None),
        ("nuri-meal", "누리군", "생활재", "슈퍼마켓", "중국음식", .91, 1.26, 1.14, 6, False, 12, .60, None, None),
        ("nuri-korean", "누리군", "생활재", "슈퍼마켓", "일반한식", .78, 1.08, .92, 6, False, 15, .55, None, None),
        ("daon-bakery", "다온시", "연령", "스넥", "제과점", .60, .80, .82, 6, False, None, None, 1.20, 1.10),
        ("daon-meal", "다온시", "기본", "스넥", "중국음식", .95, 1.22, 1.16, 6, False, 10, .60, None, None),
        ("haeon-bakery", "해온군", "기본", "중국음식", "제과점", 1.20, 1.40, 1.30, 1, False, 14, .65, None, None),
        ("saebom-meal", "새봄시", "생활재", "편의점", "중국음식", 1.10, 1.30, 1.20, 6, False, 8, .30, None, None),
    ]
    keys = "id region track anchor partner lq amount_clq count_clq months reverse stores coverage age_clq age_count_clq".split()
    result = []
    for row in rows:
        item = dict(zip(keys, row))
        item["status"], item["reason"], item["explanation"] = evaluate(item)
        result.append(item)
    return result


def worked_example():
    """표시 값 LQ=.88, CLQ=1.32를 독립 합성 집계로 다시 계산한다."""
    return {"local_total": 1000, "local_anchor": 400, "local_partner": 220,
            "reference_total": 10000, "reference_anchor": 1000, "reference_partner": 2500,
            "lq": location_quotient(220, 1000, 2500, 10000),
            "clq": conditional_lq(220, 1000, 400, 2500, 10000, 1000)}


if __name__ == "__main__":
    import json
    print(json.dumps({"data_type": "synthetic", "example": worked_example(), "records": records()}, ensure_ascii=False, indent=2))
