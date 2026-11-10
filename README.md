# 퀄컴 주요 기술 분야 분석

이 표본에서는 무선통신이 가장 큰 축이며, AI·컴퓨터 비전·비디오 코딩이 그다음의 주요 기술군으로 나타난다. 센서·음향·터치 기술도 별도 군집을 형성한다. 이는 제출된 특허 표본에 관한 결과이며 퀄컴 전체의 기술별 투자액이나 매출 구성을 뜻하지 않는다.

## 데이터와 분석 방법

- 원본: lens-export.csv, 1,000개 공개·등록 문헌, 모든 행의 Applicants에 QUALCOMM 포함.
- 공개일: 2015-01-01~2025-12-21. 2022년 문헌 321건. 검색식·정렬 방식·전체 검색 결과 규모는 제공되지 않아 표본 대표성을 확인할 수 없다.
- Simple Family Members와 Lens ID를 연결해 중복을 묶은 결과 676개 그룹. 같은 발명이 여러 국가에서 공개된 데 따른 과대 집계를 줄였다. 서로 다른 simple family에 속하는 동일·유사 제목, 분할·계속출원은 남을 수 있다.
- 영어 불용어 비율을 이용한 간이 언어 판별로 대표 문헌을 고르고 비영어권 텍스트 중심 그룹 18개를 제외했다. 최종 분석 분모는 658개 그룹이다. 자동 언어 판별의 오분류 가능성이 있다.
- 원본 초록 누락 130건. 최종 대표 문헌 중 44건은 초록이 없어 제목 중심으로 분석했다. 영어 초록으로 판별되지 않은 초록은 벡터화에서 제외했다.
- 제목+초록에 동일 가중치를 적용. 소문자화, 영어 불용어와 특허 상투어 제거, 영문 단어 및 2단어 구문 추출. min_df=3, max_df=0.85.
- TF는 1+ln(빈도), IDF는 ln((1+N)/(1+문서빈도))+1. 문서 벡터를 L2 정규화한 뒤 문서별 TF-IDF를 평균해 용어 점수를 계산했다.
- NMF 8개 주제, random_state=42. 각 문헌에서 가장 높은 주제 가중치 하나를 대표 주제로 지정했다. 주제 이름은 상위 용어와 대표 특허 제목을 보고 해석했다. 8개는 탐색용 설정이며 최적 주제 수로 검증한 것은 아니다.

## 기술 분야별 결과

비율은 658개 대표 문헌의 주제 배정 비율이며 기술의 경제적 가치나 특허의 유효성을 측정한 값이 아니다. 여러 분야에 걸친 문헌도 대표 주제 하나로 집계한다.

| 기술 분야 | 그룹 수 | 비율 | 주제 핵심어 |
|---|---:|---:|---|
| 무선 채널·전송·자원 제어 | 176 | 26.75% | channel, communication, wireless, transmission, control, uplink, wireless communication |
| 단말·기지국 통신 및 빔 제어 | 122 | 18.54% | ue, base station, station, base, user equipment, user, equipment |
| AI·머신러닝 및 관련 연산 | 80 | 12.16% | model, network, learning, machine, machine learning, neural, neural network |
| 컴퓨터 비전·3차원 인식 | 78 | 11.85% | image, object, images, pose, camera, dimensional, captured |
| 비디오 코딩·압축 | 72 | 10.94% | video, block, video data, coding, data, prediction, video coding |
| 음향·압전·MEMS 및 관련 회로 | 70 | 10.64% | transducer, piezoelectric, layer, signal, acoustic, substrate, output |
| 오디오·공간음향 | 31 | 4.71% | audio, streams, audio streams, processors, memory, rendering, audio signal |
| 터치·정전용량 센싱 | 29 | 4.41% | touch, panel, touch panel, drive, electrodes, sensor, capacitive |

무선통신 관련 두 주제를 합치면 298개, 45.29%다. 단말·기지국 간 신호 교환뿐 아니라 빔 추적, sidelink, 상향링크 제어 채널, 주파수·시간 자원 할당과 같은 구체적 제어 기술이 두드러진다. 다만 두 군집은 완전히 분리된 기술 체계가 아니며 일반적 통신 용어를 공유한다.

AI·머신러닝 군집은 80개(12.16%)로, 신경망·모델 학습과 적응·포인트클라우드 처리를 포함한다. 컴퓨터 비전 군집은 78개(11.85%)로, 물체 자세 추정·깊이·영상 복원·장면 인식이 중심이다. 두 군집을 합친 24.01%는 이 표본에서 인식·학습 기술의 존재감을 보여주지만, 모든 해당 특허가 AI를 사용하는지 또는 온디바이스에서 실행되는지는 청구항 검토 없이는 확정할 수 없다.

비디오 코딩 군집은 72개(10.94%)다. 움직임 예측·블록 단위 부호화·인트라 예측·디코딩 등이 핵심이다. 단순 영상 서비스보다 압축 효율과 복호화 절차에 관한 기술이 뚜렷하다.

음향·압전·MEMS 및 관련 회로 군집은 70개(10.64%)다. PMUT와 음향 트랜스듀서 등이 대표 사례다. 이 군집은 층·기판·회로처럼 넓은 하드웨어 용어도 공유하므로 70개 전부를 초음파 센서 특허로 해석하면 안 된다. 터치·정전용량 센싱 29개(4.41%), 오디오·공간음향 31개(4.71%)도 분리된다.

G06F가 붙은 대표 문헌은 124개지만 별도 반도체·컴퓨팅 주제로 깔끔하게 분리되지는 않았다. 따라서 이번 NMF 결과만으로 프로세서·메모리·SoC 기술의 중요도가 낮다고 단정할 수 없다.

## TF-IDF 주요 용어

아래는 전체 순위 중 해석에 유용한 용어를 선택한 것이다. 전체 순위는 tfidf_keywords.csv에 있다. TF-IDF 평균은 정규화된 상대 점수여서 확률이나 기술별 점유율로 해석하지 않는다.

| 용어 | 평균 TF-IDF | 등장 그룹 수 |
|---|---:|---:|
| ue | 0.02935 | 153 |
| wireless | 0.02343 | 191 |
| video | 0.01969 | 79 |
| image | 0.01931 | 70 |
| base station | 0.01564 | 87 |
| user equipment | 0.01504 | 141 |
| wireless communication | 0.01423 | 108 |
| uplink | 0.01290 | 58 |
| beam | 0.01184 | 40 |
| machine learning | 0.00553 | 19 |
| neural network | 0.00565 | 23 |
| pose | 0.00539 | 13 |
| video coding | 0.00680 | 38 |
| touch panel | 0.00521 | 16 |
| piezoelectric | 0.00520 | 17 |
| audio | 0.00921 | 23 |

UE는 사용자 단말을 의미한다. data, signal, information처럼 점수가 높더라도 여러 기술에 공통으로 쓰이는 단어가 있어 단어 순위만으로 기술 분야를 확정하지 않았다. NMF의 함께 나타나는 용어와 대표 문헌, CPC를 함께 확인했다. 외부 경쟁사 문헌을 포함하지 않았으므로 이 점수는 경쟁사 대비 차별성을 측정하지 않는다.

## CPC 교차 확인

다음은 분석 대상 대표 문헌에 실제 부여된 CPC의 앞 4자리 집계다. 한 그룹에 여러 코드가 있으므로 합계는 658을 넘을 수 있다. 제외된 언어 그룹의 CPC는 집계하지 않았다.

| CPC | 대표 그룹 수 |
|---|---:|
| H04W | 262 |
| H04L | 223 |
| G06F | 124 |
| H04B | 116 |
| H04N | 103 |
| G06N | 67 |
| G06T | 66 |
| G06V | 55 |
| Y02D | 45 |
| H04R | 30 |
| G10L | 26 |
| G01S | 17 |
| G01R | 14 |
| H04J | 14 |
| H10N | 13 |

H04W·H04L·H04B가 상위라는 점은 통신 중심이라는 텍스트 분석과 일치한다. H04N, G06N, G06T, G06V의 존재도 비디오·AI·영상 인식 군집을 뒷받침한다. CPC만으로 세부 제품, 특정 표준 채택, 표준필수특허 여부를 판정하지 않았다.

## 주제별 대표 문헌

아래 링크는 원본 CSV에 수록된 URL이며 링크의 외부 내용을 추가 검증한 것은 아니다.

### 단말·기지국 통신 및 빔 제어

- [VIRTUAL SERVING BEAM TRACKING IN MILLIMETER WAVE WIRELESS SYSTEMS](https://lens.org/139-785-553-632-395)
- [REFERENCE SIGNAL DESIGN](https://lens.org/127-728-352-409-078)

### 비디오 코딩·압축

- [Coding affine prediction motion information for video coding](https://lens.org/063-870-489-460-269)
- [Intra BC and inter unification](https://lens.org/135-382-071-132-011)

### 컴퓨터 비전·3차원 인식

- [Three-dimensional pose estimation of symmetrical objects](https://lens.org/130-968-312-908-711)
- [POSE ESTIMATION FOR IMAGE RECONSTRUCTION](https://lens.org/098-579-458-174-67X)

### 터치·정전용량 센싱

- [Capacitive touch panel configured to sense both active and passive input with a single sensor](https://lens.org/153-349-545-376-009)
- [ORTHOGONAL FREQUENCY DIVISION SCANNING METHOD FOR SENSORS](https://lens.org/006-114-861-974-004)

### 무선 채널·전송·자원 제어

- [METHODS FOR UPLINK COMMUNICATION IN A SHARED BAND OF A RADIO-FREQUENCY SPECTRUM](https://lens.org/135-772-552-473-769)
- [BROADCASTING TRANSMISSION OF MESSAGES BASED ON CONTROL CHANNEL](https://lens.org/113-851-439-039-327)

### 음향·압전·MEMS 및 관련 회로

- [ACOUSTIC TRANSDUCER SYSTEM WITH FEEDBACK TRANSDUCTION](https://lens.org/123-497-082-319-679)
- [ACOUSTIC TRANSDUCER SYSTEM WITH FEEDBACK TRANSDUCTION](https://lens.org/157-215-830-698-201)

### AI·머신러닝 및 관련 연산

- [SELF-SUPERVISED POINT CLOUD ORDERING USING MACHINE LEARNING MODELS](https://lens.org/122-932-562-675-32X)
- [SELF-SUPERVISED POINT CLOUD ORDERING USING MACHINE LEARNING MODELS](https://lens.org/193-851-373-064-555)

### 오디오·공간음향

- [PRIVACY ZONING AND AUTHORIZATION FOR AUDIO RENDERING](https://lens.org/026-322-218-674-08X)
- [USER INTERFACE FOR CONTROLLING AUDIO RENDERING FOR EXTENDED REALITY EXPERIENCES](https://lens.org/081-740-868-518-683)

## 해석의 범위와 후속 분석

이 표본은 “무선 연결 + 학습·인식 + 멀티미디어 처리 + 센싱”이라는 기술 조합을 보여준다. 실제 제품 전략에 대한 해석은 이 특허 조합으로부터의 추론이다. 특허 건수만으로 매출 기여도·시장 우위·권리 강도를 평가할 수 없다.

연도별 원시 건수는 국가별 공개 시차, 등록·공개 중복, 검색 결과의 추출 방식에 영향을 받는다. 특히 2022년 집중을 연구개발 급증으로 해석하지 않았다. 기술 부상·쇠퇴를 확인하려면 전체 검색식과 추출 범위를 확보하고 패밀리별 최초 우선일을 기준으로 코호트를 비교해야 한다. 경쟁사와 동일 조건으로 비교하면 퀄컴에 특화된 용어와 기술을 더 정확하게 평가할 수 있다.

재현: Downloads에서 `python qualcomm_analysis.py` 실행. 원본 CSV는 변경하지 않았다. 그래프는 technology_analysis.png, 전체 키워드는 tfidf_keywords.csv, 패밀리별 배정은 family_topics.csv, 수치는 results.json에 있다.
