# MorningBriefBot

매일 아침 시장 브리프를 카드뉴스 이미지로 만들어 Instagram과 TikTok에 자동으로 올리는 파이프라인.

## 동작 방식

```
Claude 예약 작업(매일 아침, cron)
  1. 웹 검색으로 오늘의 시장 데이터를 모아 data/brief_data.json 작성
  2. python src/main.py 실행
       a. src/generate_cards.py    -> docs/<날짜>/card_XX.png 카드뉴스 이미지 생성
       b. src/publish_pages.py     -> git commit+push, GitHub Pages에 반영될 때까지 대기
       c. src/instagram_post.py    -> 이미지 URL들을 Instagram 캐러셀로 게시
       d. src/tiktok_post.py       -> 이미지 URL들을 TikTok 포토 게시물로 게시
```

이미지를 Instagram/TikTok API에 넘기려면 "누구나 접근 가능한 URL"이 있어야 하는데, 이 프로젝트는
GitHub Pages(`docs/` 폴더)를 그 호스팅으로 씁니다. 그래서 매일 이미지가 이 repo에 커밋·푸시됩니다.

## 0. 로컬 설치

```bash
pip install -r requirements.txt
cp .env.example .env
```

`.env`는 절대 git에 커밋되지 않습니다 (`.gitignore`에 포함).

카드 이미지만 로컬에서 테스트하려면:

```bash
python src/generate_cards.py --input data/brief_data.schema.json --outdir docs/test
```

`docs/test/card_01.png` 등을 열어서 확인한 뒤 지워도 됩니다.

## 1. GitHub 저장소 + Pages ✅ (완료)

- 저장소: https://github.com/moonkj/MorningBriefBot (public — 카드 이미지가 어차피 SNS에
  공개되므로 public으로 전환. `.env`는 `.gitignore`에 있어 올라가지 않음)
- GitHub Pages: https://moonkj.github.io/MorningBriefBot/ (source: `main` / `/docs`, 확인 완료)
- `.env`에 `GITHUB_USERNAME=moonkj`, `GITHUB_REPO=MorningBriefBot` 이미 채워져 있음.

## 2. Instagram (Meta Graph API) 설정

Instagram Graph API의 게시(publish) 기능은 **프로페셔널(비즈니스/크리에이터) 계정**에만 있고,
그 계정이 **Facebook 페이지**와 연결되어 있어야 합니다.

1. Instagram 앱에서: 설정 → 계정 유형을 "프로페셔널 계정(비즈니스)"으로 전환.
2. Facebook에서 페이지가 없다면 하나 생성하고, 위 Instagram 계정과 연결(Instagram 계정 설정에서 "연결된 계정").
3. https://developers.facebook.com/apps 에서 새 앱 생성 (유형: 비즈니스).
4. 앱에 **Instagram Graph API** 제품 추가.
5. 앱 대시보드 → **Graph API Explorer**로 이동:
   - 내 앱 선택 → User Token 요청 시 권한에 `instagram_basic`, `instagram_content_publish`,
     `pages_show_list`, `pages_read_engagement` 추가.
   - `GET /me/accounts` 호출 → 내 Facebook 페이지의 `id`와 `access_token`(페이지 토큰) 확인.
   - `GET /<페이지ID>?fields=instagram_business_account` 호출 → `IG_USER_ID` 확인.
6. 페이지 토큰은 기본 1~2시간짜리 단기 토큰이므로, 장기 토큰(약 60일)으로 교환:
   ```bash
   python scripts/instagram_token_exchange.py --short-token <5단계에서 받은 토큰>
   ```
   `.env`의 `META_APP_ID`, `META_APP_SECRET`을 먼저 채워야 합니다 (앱 대시보드 → 설정 → 기본 정보).
7. 나온 값을 `.env`의 `IG_USER_ID`, `IG_ACCESS_TOKEN`에 채우기.

> 참고: 이 앱을 본인 계정에만 쓸 거라면(다른 사람 계정에 게시하지 않음) Meta의 정식 App Review 없이
> "개발 모드 + 본인을 앱의 테스터/관리자로 추가"만으로 충분한 경우가 많습니다. 화면에 안내가 뜨면
> 그대로 따라가면 됩니다. 토큰은 약 60일마다 재발급이 필요합니다.

## 3. TikTok (Content Posting API) 설정

1. https://developers.tiktok.com/ 에서 개발자 계정 생성 → 새 앱 생성.
2. 앱에 **Content Posting API** 제품(Login Kit 포함) 추가.
3. 앱 설정 → Redirect URI에 정확히 `http://localhost:8787/callback` 등록.
4. 앱 설정 → **URL Properties / 도메인 소유권 검증**: `<GITHUB_USERNAME>.github.io`를 등록하고
   TikTok이 요구하는 검증 파일을 `docs/` 최상단에 추가 후 commit/push
   (PULL_FROM_URL로 그 도메인의 이미지를 가져오려면 이 검증이 필요합니다).
5. `.env`에 `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` 채우기 (앱 대시보드에서 확인).
6. 최초 1회, 본인 계정으로 로그인해 access token 발급:
   ```bash
   python scripts/tiktok_oauth.py
   ```
   브라우저가 열리면 본인 TikTok 계정으로 로그인/동의 → 터미널에 토큰이 출력되면
   `.env`의 `TIKTOK_ACCESS_TOKEN`에 채우기.

> **중요한 제약**: 새로 만든 앱은 기본적으로 "심사 전(Unaudited)" 상태이고, 이 상태에서는
> `privacy_level`을 `SELF_ONLY`로만 게시할 수 있습니다 (본인 계정에서만 보이는 비공개 게시,
> 실제 공개 피드/포유 화면에는 노출되지 않음). 공개 계정에 실제로 자동 게시하려면 TikTok
> 개발자 콘솔에서 **App Review(콘텐츠 게시 심사)** 를 신청해서 통과해야 합니다 — 이건 TikTok
> 쪽 정책이라 제가 대신 처리할 수 없고, 신청 후 심사에 며칠~몇 주가 걸릴 수 있습니다.
> 심사 전까지는 SELF_ONLY로 파이프라인이 잘 도는지 먼저 검증하는 용도로 쓰세요.

## 4. 브랜드 설정

`.env`의 `BRAND_HANDLE`을 카드 하단에 표시할 계정 핸들로 설정하세요 (예: `@your_handle`).

## 5. 파이프라인 수동 테스트

API 키를 다 채운 뒤, 오늘자 `data/brief_data.json`을 하나 만들고 (형식은
`data/brief_data.schema.json` 참고) 아래로 부분 테스트할 수 있습니다.

```bash
# 카드 생성 + GitHub Pages 반영만 (SNS 게시는 건너뜀)
python src/main.py --input data/brief_data.json --skip-instagram --skip-tiktok

# Instagram만
python src/main.py --input data/brief_data.json --skip-tiktok

# 전체
python src/main.py --input data/brief_data.json
```

## 6. 예약 작업

API 설정이 끝나고 수동 테스트가 성공하면, Claude의 예약 작업(스케줄러)으로 매일 아침 자동 실행되게
설정합니다. 이 repo가 준비되면 알려주세요 — 예약 작업을 등록해 드립니다.

## 한계 / 주의사항

- **TikTok**: 위에서 설명한 대로 App Review 전에는 본인만 보이는 비공개 게시만 가능합니다.
- **Instagram 토큰**: 장기 토큰도 약 60일 후 만료됩니다. 만료되면
  `scripts/instagram_token_exchange.py`로 재발급하거나 새로 Graph API Explorer에서 토큰을
  받아야 합니다.
- **GitHub Pages 반영 지연**: push 후 실제로 이미지가 열리기까지 수십 초~몇 분이 걸릴 수 있어
  `publish_pages.py`가 최대 5분간 폴링합니다.
- **캐러셀 장수**: Instagram/TikTok 모두 캐러셀은 최대 10장입니다. 브리프 섹션이 많으면
  카드가 10장을 넘을 수 있으니, `brief_data.json`을 채울 때 핵심만 추려서 8~9장 이내로
  유지하는 걸 권장합니다.
