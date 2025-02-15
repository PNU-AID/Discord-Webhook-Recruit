# 취업 정보 알림 봇 (Discord Webhook)

이 앱은 [IN THIS WORK - IT개발](https://inthiswork.com/?s=IT%EA%B0%9C%EB%B0%9C) 페이지에 게시된 채용정보를 스크래핑하여 Discord Webhook을 통해 특정 Discord 채널로 알림을 전송합니다.

아래 조건에 해당하는 채용 공고가 전송됩니다.

- AI와 관련된 직무
- 경력직 제외

## 기능

- [IN THIS WORK - IT개발](https://inthiswork.com/?s=IT%EA%B0%9C%EB%B0%9C)
- 회사, 채용 제목, 채용정보 링크를 Git Action을 사용하여 주기적으로 Discord로 전송.
- 환경 변수로 Discord URL(알림을 전송할 채널) 설정 가능.

## 출력 예시

```
[오늘의 채용 공고]

공고: (주)AID｜2025년 상반기 정규채용
링크: https://inthiswork.com/archives/000000

공고: AID Brain｜AI Research(체험형 인턴)
링크: https://inthiswork.com/archives/000000

...
```

## 알림 전송 과정

1. Github Actions(설정된 시각에 자동 시작)
2. `bun run scheduling` 스크립트 실행
3. `src/app.ts` 실행 - 알림 내용(텍스트) 완성
4. 디스코드 채널에 알림 전송

## 환경 변수

```bash
# 알림을 전송할 디스코드 채널의 웹훅 URL
# 웹훅 URL은 디스코드 서버 설정 - 연동에서 확인 가능
# 참고: https://www.svix.com/resources/guides/how-to-make-webhook-discord/
AID_DISCORD_WEBHOOK_URL='Your Webhook URL'
```

## 제한 사항 & 개선해야할 점

- IN THIS WORK 홈페이지만 참고 중, 다른 사이트도 포함하면 좋을 것 같습니다.
- 비동기 알고리즘 강화 필요, 현재 10개까지 전송 가능. job.ts TODO 표시 주석 참고

## 프로젝트 구조

```bash
📁.github ─ 📁workflows ─ 📜schedule.yml # 자동으로 알림을 발송하기 위한 Actions 스크립트
📁data ─ 📁data ─ 📚homepage.json # 스크래핑할 페이지 정보
📁src ┬ 📁type # 프로젝트에 필요한 Type이 정리된 폴더
🔹    ├ 📁utils # 사용되는 핵심 함수 및 클래스등으로 이루어진 유틸리티를 담은 폴더
🔹    └ 📑app.ts # 프로젝트 메인 실행 파일
📜.gitignore
📜bun.lock # bun의 종속성 관리 파일
📜package.json # 패키지 정보 및 필수 모듈을 담은 파일
📜README.md
📜tsconfig.json # Typescript 설정 파일
```

## 요구 사항

- Bun v1.2.2 이상
  - Node.js와 호환 가능하나, 실행 스크립트와 종속성이 Bun에 맞춰져 있음.
- package
  - dependencies
    - @huggingface/transformers@3.3.3
      - Transformer, 채용 공고가 AI와 관련 있는 공고인지 판단하기 위해 사용
    - @types/node-cron@3.0.11
      - node-cron의 Type이 정의됨
    - axios@1.6.7
      - REST API
    - cheerio@1.0.0-rc.12
      - HTML을 파싱하고 쉽게 조작
    - dotenv@16.4.5
      - 환경변수 파일 리딩
  - devDependencies
    - @types/node@20.11.25
      - node의 Type이 정의됨
    - ts-node@10.9.2
      - ts파일을 실행하기 위한 패키지
    - typescript@5.4.2
      - js에 타입을 추가한 typescript
