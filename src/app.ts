import dotenv from "dotenv";

import { crawlWebsite } from "./utils/job";

dotenv.config();

async function main() {
  // 매일 대한민국 오후 8시에 실행
  console.log("크롤링 작업을 시작합니다.");
  await crawlWebsite();
  console.log("크롤링 작업이 종료되었습니다.");
}

(async () => {
  await main();
  process.exit(0);
})();
