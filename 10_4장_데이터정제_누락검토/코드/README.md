# 재현 코드

`build_chapter4_candidates.py`는 후보 목록의 범위·패밀리 연결을 확인하고 집계표와 그래프를 생성한다. Python 3.11 환경에서 pandas, numpy, matplotlib을 사용했다. 한글 그래프는 맑은 고딕을 사용한다.

다음 원자료를 한 폴더에 준비한다.

- `missing_query_candidates_LOCAL.csv`
- `v2_Lens_퀄컴_무선통신_요약전수검토_2015-2024.csv`
- `lens-export.csv`
- `qualcom.csv`
- `qualcom1.csv`

저장소 루트에서 다음과 같이 실행한다.

```powershell
python "10_4장_데이터정제_누락검토/코드/build_chapter4_candidates.py" --inputs "<원자료 폴더>" --repo "." --local "../chapter4_review_local"
```

집계표와 그림은 해당 장의 폴더에 생성된다. 원문이 포함된 대표 문헌 목록은 `--local`로 지정한 폴더에 저장된다. 원본 입력 파일은 읽기 전용으로 사용한다.

패밀리 연결은 이전 세 CSV와 v2 CSV를 함께 사용해 구성원 ID의 연결 성분으로 계산한다. 대표 문헌은 초록 존재 여부, 공개일, Lens ID 순서로 선택한다. CPC 후보 비율은 후보 패밀리당 중복 제거, 본 분석 비율은 문헌당 중복 제거 방식이다.

이 코드는 이미 생성된 후보 CSV를 점검하는 후속 코드다. KIPRIS 검색식을 실제 실행하거나 초기 후보의 정규식 매칭을 재현하지 않는다. 후보 CSV의 `title_terms`는 리스트 리터럴로 파싱하며 코드로 실행하지 않는다. 원검색 조건과 로컬 근사 매칭의 차이는 제4장 4.1.2절에 설명했다.
